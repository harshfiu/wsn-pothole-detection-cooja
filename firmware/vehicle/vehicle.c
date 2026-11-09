/* Vehicle-mounted sensor node.
 *
 * Cooja has no road surface or GPS, so both are SYNTHESISED here:
 *  - position follows the same back-and-forth path the simulation script
 *    uses to move the mote;
 *  - acceleration is low noise, plus a spike when passing a pothole.
 * Detection on the node is real: 10 Hz sampling, peak over a 5 s window,
 * threshold classification. Each window is one broadcast report.
 *
 * Built WITHOUT RPL (see this folder's Makefile): a moving vehicle must never
 * become a router or a parent in the roadside tree. */
#include "../pothole.h"
#include "net/ip/uip.h"
#include "net/ipv6/uip-ds6.h"
#include "simple-udp.h"
#include "node-id.h"
#include "lib/random.h"
#include <string.h>

#define ROAD_M         140L
#define SPEED_MPS      8L
#define FIRST_VEH_ID   8
#define PHASE_M        35L
#define WINDOW_SAMPLES 50

#define BASE_LAT_E6    12823000L
#define BASE_LON_E6    80044400L
#define LON_E6_PER_10M 92L  /* about 9.2 micro-degrees of longitude per metre */

static const struct { uint8_t x; uint16_t amp; } potholes[] = {
  {  22, 1050 }, {  48, 1650 }, {  77,  550 }, { 103, 1650 }, { 126, 1050 },
};
#define NUM_POTHOLES (sizeof(potholes) / sizeof(potholes[0]))

static struct simple_udp_connection conn;

static int
position_m(void)
{
  long p = (long)((unsigned long)clock_time() * SPEED_MPS / CLOCK_SECOND);
  p = (p + (node_id - FIRST_VEH_ID) * PHASE_M) % (2 * ROAD_M);
  return (int)(p <= ROAD_M ? p : 2 * ROAD_M - p);
}

static uint16_t
sample_accel_mg(int x)
{
  uint16_t i, mg = 20 + random_rand() % 100;
  for(i = 0; i < NUM_POTHOLES; i++) {
    if(x >= (int)potholes[i].x - 2 && x <= (int)potholes[i].x + 2) {
      /* amplitude +/- 15% */
      mg = potholes[i].amp - potholes[i].amp * 15 / 100
         + random_rand() % (potholes[i].amp * 30 / 100 + 1);
    }
  }
  return mg;
}

static uint8_t
classify(uint16_t mg)
{
  return mg >= 1300 ? 3 : mg >= 800 ? 2 : mg >= 350 ? 1 : 0;
}

static void
udp_rx(struct simple_udp_connection *c, const uip_ipaddr_t *src,
       uint16_t sport, const uip_ipaddr_t *dst, uint16_t dport,
       const uint8_t *data, uint16_t len)
{
}

PROCESS(vehicle_process, "Pothole vehicle node");
AUTOSTART_PROCESSES(&vehicle_process);

PROCESS_THREAD(vehicle_process, ev, data)
{
  static struct etimer et;
  static uip_ipaddr_t all_nodes;
  static struct report r;
  static uint16_t seq, peak, n, windows;
  static int peak_x;
  uint16_t mg;
  int x;
  PROCESS_BEGIN();

  simple_udp_register(&conn, VEHICLE_PORT, NULL, VEHICLE_PORT, udp_rx);
  uip_create_linklocal_allnodes_mcast(&all_nodes);
  random_init(node_id);
  printf("BOOT,vehicle,%d\n", node_id);

  /* Give the roadside tree time to form before reporting. */
  etimer_set(&et, 60 * CLOCK_SECOND);
  PROCESS_WAIT_UNTIL(etimer_expired(&et));

  etimer_set(&et, CLOCK_SECOND / 10);
  while(1) {
    PROCESS_WAIT_UNTIL(etimer_expired(&et));
    etimer_reset(&et);

    x = position_m();
    mg = sample_accel_mg(x);
    if(mg > peak) {
      peak = mg;
      peak_x = x;
    }

    if(++n >= WINDOW_SAMPLES) {
      r.vehicle = node_id;
      r.seq = ++seq;
      r.peak_mg = peak;
      r.severity = classify(peak);
      r.lat_e6 = BASE_LAT_E6;
      r.lon_e6 = BASE_LON_E6 + (long)peak_x * LON_E6_PER_10M / 10;
      printf("TX,%d,%u,%u,%d,%d\n", node_id, r.seq, r.peak_mg, r.severity, peak_x);
      simple_udp_sendto(&conn, &r, sizeof(r), &all_nodes);
      n = 0;
      peak = 0;
      if(++windows >= 6) {
        windows = 0;
        log_energy(node_id);
      }
    }
  }
  PROCESS_END();
}
