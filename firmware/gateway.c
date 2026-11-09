/* Roadside gateway / cluster head: static RPL router. Collects one-hop
 * broadcasts from passing vehicles, drops duplicates, batches records and
 * forwards them to the sink over the RPL tree. */
#include "pothole.h"
#include "net/ip/uip.h"
#include "net/ipv6/uip-ds6.h"
#include "net/rpl/rpl.h"
#include "simple-udp.h"
#include "node-id.h"
#include <string.h>

#define SEEN_SIZE 8

static struct simple_udp_connection veh_conn, sink_conn;
static struct aggregate buf;
static struct { uint8_t vehicle; uint16_t seq; } seen[SEEN_SIZE];
static uint8_t seen_next;
static struct ctimer flush_timer;
static int last_parent = -1;

static void
flush(void *unused)
{
  rpl_dag_t *dag = rpl_get_any_dag();
  ctimer_stop(&flush_timer);
  if(buf.count == 0) {
    return;
  }
  if(dag != NULL && dag->preferred_parent != NULL) {
    buf.gateway = node_id;
    simple_udp_sendto(&sink_conn, &buf,
                      2 + buf.count * sizeof(struct report), &dag->dag_id);
    printf("FWD,%d,%d\n", node_id, buf.count);
  } else {
    printf("DROP,%d,%d\n", node_id, buf.count);
  }
  buf.count = 0;
}

static void
vehicle_rx(struct simple_udp_connection *c, const uip_ipaddr_t *src,
           uint16_t sport, const uip_ipaddr_t *dst, uint16_t dport,
           const uint8_t *data, uint16_t len)
{
  struct report r;
  int i;
  if(len != sizeof(r)) {
    return;
  }
  memcpy(&r, data, len);
  for(i = 0; i < SEEN_SIZE; i++) {
    if(seen[i].vehicle == r.vehicle && seen[i].seq == r.seq) {
      return;
    }
  }
  seen[seen_next].vehicle = r.vehicle;
  seen[seen_next].seq = r.seq;
  seen_next = (seen_next + 1) % SEEN_SIZE;

  buf.rec[buf.count++] = r;
  if(buf.count >= RECS_PER_FRAME) {
    flush(NULL);
  } else if(buf.count == 1) {
    ctimer_set(&flush_timer, FLUSH_SECONDS * CLOCK_SECOND, flush, NULL);
  }
}

static void
sink_rx(struct simple_udp_connection *c, const uip_ipaddr_t *src,
        uint16_t sport, const uip_ipaddr_t *dst, uint16_t dport,
        const uint8_t *data, uint16_t len)
{
}

static void
check_parent(void)
{
  rpl_dag_t *dag = rpl_get_any_dag();
  int p = 0;
  if(dag != NULL && dag->preferred_parent != NULL) {
    uip_ipaddr_t *ip = rpl_get_parent_ipaddr(dag->preferred_parent);
    p = ip != NULL ? ip->u8[15] : 0;
  }
  if(p != last_parent) {
    printf("PARENT,%d,%d\n", node_id, p);
    last_parent = p;
  }
}

PROCESS(gateway_process, "Pothole gateway");
AUTOSTART_PROCESSES(&gateway_process);

PROCESS_THREAD(gateway_process, ev, data)
{
  static struct etimer et;
  static uint8_t ticks;
  PROCESS_BEGIN();

  simple_udp_register(&veh_conn, VEHICLE_PORT, NULL, VEHICLE_PORT, vehicle_rx);
  simple_udp_register(&sink_conn, SINK_PORT, NULL, SINK_PORT, sink_rx);
  printf("BOOT,gateway,%d\n", node_id);

  etimer_set(&et, CLOCK_SECOND);
  while(1) {
    PROCESS_WAIT_UNTIL(etimer_expired(&et));
    etimer_reset(&et);
    check_parent();
    if(++ticks >= 30) {
      ticks = 0;
      log_energy(node_id);
    }
  }
  PROCESS_END();
}
