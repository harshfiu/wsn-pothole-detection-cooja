/* Shared definitions for the sink, roadside gateways and vehicle nodes. */
#ifndef POTHOLE_H_
#define POTHOLE_H_

#include "contiki.h"
#include "sys/energest.h"
#include <stdio.h>

#define VEHICLE_PORT 8765  /* one-hop vehicle -> gateway broadcasts */
#define SINK_PORT    5678  /* gateway -> sink over RPL              */

#define RECS_PER_FRAME 3   /* a gateway flushes after 3 records...   */
#define FLUSH_SECONDS  2   /* ...or after 2 seconds, whichever first */

/* One road-condition report. */
struct report {
  uint8_t  vehicle;
  uint16_t seq;
  uint16_t peak_mg;   /* peak vertical acceleration in the window, milli-g */
  uint8_t  severity;  /* 0 none, 1 low, 2 medium, 3 high                   */
  int32_t  lat_e6;    /* latitude  x 10^6 */
  int32_t  lon_e6;    /* longitude x 10^6 */
} __attribute__((packed));

/* Aggregated frame sent from a gateway to the sink. */
struct aggregate {
  uint8_t gateway;
  uint8_t count;
  struct report rec[RECS_PER_FRAME];
} __attribute__((packed));

/* Cumulative time per power state, in rtimer ticks (32768 per second). */
static inline void
log_energy(int node)
{
  energest_flush();
  printf("ENERGY,%d,%lu,%lu,%lu,%lu\n", node,
         (unsigned long)energest_type_time(ENERGEST_TYPE_CPU),
         (unsigned long)energest_type_time(ENERGEST_TYPE_LPM),
         (unsigned long)energest_type_time(ENERGEST_TYPE_TRANSMIT),
         (unsigned long)energest_type_time(ENERGEST_TYPE_LISTEN));
}

#endif
