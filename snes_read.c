/*
 * SNES controller passive reader + MQTT light control + ADB TV remote.
 * Simple state machine: debounce press → fire → cooldown → wait for release.
 *
 * X      = toggle light 1 (tasmota_952D74)
 * Y      = toggle light 2 (tasmota_93D272)
 * UP/DOWN/LEFT/RIGHT = DPAD navigation on Android TV
 * A      = ENTER (select)
 * B      = BACK
 * START  = POWER (toggle TV on/off)
 * SELECT = MENU
 * L      = PAGE_UP
 * R      = PAGE_DOWN
 *
 * GPIO 17 = Clock, GPIO 27 = Latch, GPIO 22 = Data
 * Compile: gcc -O2 -o snes_read snes_read.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <sys/wait.h>
#include <errno.h>

#define BLOCK_SIZE 4096
#define GPLEV0 13

#define CLOCK_PIN 17
#define LATCH_PIN 27
#define DATA_PIN  22

#define NUM_BUTTONS 12
#define PRESS_FRAMES 4       /* consecutive pressed frames to trigger */
#define RELEASE_FRAMES 4     /* consecutive released frames to re-arm */
#define COOLDOWN_MS 400      /* ignore button for this long after firing */

static volatile unsigned *gpio;
static volatile int running = 1;

/* --- MQTT config (from environment) --- */
static const char *mqtt_host;
static const char *mqtt_port;
static const char *mqtt_user;
static const char *mqtt_pass;
static const char *topic_light1;
static const char *topic_light2;

static int light1_on = 0;
static int light2_on = 0;

/* --- ADB config --- */
#define ADB_FIFO "/tmp/snes_adb"

static FILE *adb_fifo = NULL;

enum state { IDLE, COOLDOWN, WAIT_RELEASE };

static inline int gpio_read(int pin) {
    return (*(gpio + GPLEV0) >> pin) & 1;
}

void handle_sigint(int sig) {
    (void)sig;
    running = 0;
}

static long long now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

/* --- MQTT: fire-and-forget via mosquitto_pub --- */
void mqtt_publish(const char *topic, const char *payload) {
    pid_t pid = fork();
    if (pid == 0) {
        int devnull = open("/dev/null", O_WRONLY);
        if (devnull >= 0) { dup2(devnull, STDOUT_FILENO); dup2(devnull, STDERR_FILENO); close(devnull); }
        execlp("mosquitto_pub", "mosquitto_pub",
               "-h", mqtt_host, "-p", mqtt_port,
               "-u", mqtt_user, "-P", mqtt_pass,
               "-t", topic, "-m", payload, NULL);
        _exit(1);
    }
    while (waitpid(-1, NULL, WNOHANG) > 0);
}

/* --- ADB: write keycode to FIFO (read by snes_adb_daemon.py) --- */
static void adb_open_fifo(void) {
    /* O_NONBLOCK + O_WRONLY: succeeds only if reader is already open */
    int fd = open(ADB_FIFO, O_WRONLY | O_NONBLOCK);
    if (fd >= 0) {
        adb_fifo = fdopen(fd, "w");
        if (adb_fifo) setvbuf(adb_fifo, NULL, _IOLBF, 0);
    }
}

static void adb_keyevent(const char *keycode) {
    if (!adb_fifo) adb_open_fifo();
    if (!adb_fifo) return;  /* daemon not running yet */
    if (fprintf(adb_fifo, "%s\n", keycode) < 0) {
        fclose(adb_fifo);
        adb_fifo = NULL;
    }
}

/* --- Button → ADB keycode map (NULL = no ADB action) --- */
static const char *adb_keymap[NUM_BUTTONS] = {
    /* B */      "KEYCODE_BACK",
    /* Y */      NULL,
    /* SELECT */ "KEYCODE_MENU",
    /* START */  "KEYCODE_TV_POWER",
    /* UP */     "KEYCODE_DPAD_UP",
    /* DOWN */   "KEYCODE_DPAD_DOWN",
    /* LEFT */   "KEYCODE_DPAD_LEFT",
    /* RIGHT */  "KEYCODE_DPAD_RIGHT",
    /* A */      "KEYCODE_ENTER",
    /* X */      NULL,
    /* L */      "KEYCODE_PAGE_UP",
    /* R */      "KEYCODE_PAGE_DOWN",
};

int main(void) {
    /* Load config from environment */
    mqtt_host    = getenv("MQTT_HOST");
    mqtt_port    = getenv("MQTT_PORT");
    mqtt_user    = getenv("MQTT_USER");
    mqtt_pass    = getenv("MQTT_PASS");
    topic_light1 = getenv("MQTT_topic_light1");
    topic_light2 = getenv("MQTT_topic_light2");

    if (!mqtt_host || !mqtt_port || !mqtt_user || !mqtt_pass ||
        !topic_light1 || !topic_light2) {
        fprintf(stderr, "Missing env vars. Source .env first:\n");
        fprintf(stderr, "  MQTT_HOST MQTT_PORT MQTT_USER MQTT_PASS\n");
        fprintf(stderr, "  MQTT_topic_light1 MQTT_topic_light2\n");
        return 1;
    }

    int fd = open("/dev/gpiomem", O_RDWR | O_SYNC);
    if (fd < 0) { perror("open /dev/gpiomem"); return 1; }

    gpio = (volatile unsigned *)mmap(NULL, BLOCK_SIZE,
                                      PROT_READ | PROT_WRITE,
                                      MAP_SHARED, fd, 0);
    close(fd);
    if (gpio == MAP_FAILED) { perror("mmap"); return 1; }

    *(gpio + 1) &= ~(7 << 21);  /* GPIO 17 input */
    *(gpio + 2) &= ~(7 << 6);   /* GPIO 22 input */
    *(gpio + 2) &= ~(7 << 21);  /* GPIO 27 input */

    signal(SIGINT, handle_sigint);
    signal(SIGTERM, handle_sigint);

    /* Try to open FIFO — non-fatal if daemon not running yet */
    adb_open_fifo();

    const char *buttons[] = {
        "B", "Y", "Select", "Start",
        "Up", "Down", "Left", "Right",
        "A", "X", "L", "R"
    };
    enum { BTN_B=0, BTN_Y, BTN_SELECT, BTN_START,
           BTN_UP, BTN_DOWN, BTN_LEFT, BTN_RIGHT,
           BTN_A, BTN_X, BTN_L, BTN_R };

    enum state state[NUM_BUTTONS];
    int counter[NUM_BUTTONS];
    long long cooldown_end[NUM_BUTTONS];

    for (int i = 0; i < NUM_BUTTONS; i++) {
        state[i] = IDLE;
        counter[i] = 0;
        cooldown_end[i] = 0;
    }

    printf("SNES controller → lights + Android TV (via ADB daemon)\n");
    printf("  X/Y    = toggle lights\n");
    printf("  D-pad/A/B/L/R/Select = TV navigation\n");
    printf("  Start  = TV power\n");
    printf("Ctrl+C to stop.\n\n");
    fflush(stdout);

    while (running) {
        /* Wait for latch pulse */
        while (running && !gpio_read(LATCH_PIN));
        while (running && gpio_read(LATCH_PIN));
        if (!running) break;

        /* Read 12 bits on clock edges */
        int bits[NUM_BUTTONS];
        for (int i = 0; i < NUM_BUTTONS; i++) {
            while (gpio_read(CLOCK_PIN));
            bits[i] = gpio_read(DATA_PIN);
            while (!gpio_read(CLOCK_PIN));
        }

        long long t = now_ms();

        for (int i = 0; i < NUM_BUTTONS; i++) {
            int pressed = (bits[i] == 0);

            switch (state[i]) {
            case IDLE:
                if (pressed) {
                    counter[i]++;
                    if (counter[i] >= PRESS_FRAMES) {
                        printf("Pressed: %s", buttons[i]);

                        /* Light control */
                        if (i == BTN_X) {
                            light1_on = !light1_on;
                            const char *p = light1_on ? "ON" : "OFF";
                            mqtt_publish(topic_light1, p);
                            printf(" → Light 1 %s", p);
                        } else if (i == BTN_Y) {
                            light2_on = !light2_on;
                            const char *p = light2_on ? "ON" : "OFF";
                            mqtt_publish(topic_light2, p);
                            printf(" → Light 2 %s", p);
                        }

                        /* ADB TV control */
                        if (adb_keymap[i]) {
                            adb_keyevent(adb_keymap[i]);
                            printf(" → %s", adb_keymap[i]);
                        }

                        printf("\n");
                        fflush(stdout);

                        state[i] = COOLDOWN;
                        cooldown_end[i] = t + COOLDOWN_MS;
                        counter[i] = 0;
                    }
                } else {
                    counter[i] = 0;
                }
                break;

            case COOLDOWN:
                if (t >= cooldown_end[i]) {
                    state[i] = WAIT_RELEASE;
                    counter[i] = 0;
                }
                break;

            case WAIT_RELEASE:
                if (!pressed) {
                    counter[i]++;
                    if (counter[i] >= RELEASE_FRAMES) {
                        state[i] = IDLE;
                        counter[i] = 0;
                    }
                } else {
                    counter[i] = 0;
                }
                break;
            }
        }
    }

    if (adb_fifo) fclose(adb_fifo);
    printf("\nDone.\n");
    return 0;
}
