/* Sink / base station: RPL DODAG root. Receives aggregates from gateways
 * and logs every record for the monitoring server. */
#include "pothole.h"
#include "net/ip/uip.h"
#include "net/ipv6/uip-ds6.h"
#include "net/rpl/rpl.h"
#include "simple-udp.h"
#include "node-id.h"
#include "net/netstack.h"
#include <string.h>

#define IP_BUF ((struct uip_ip_hdr *)&uip_buf[UIP_LLH_LEN])

static struct simple_udp_connection gw_conn, veh_conn;

static void
print_record(int via, int hops, const struct report *r)
{
  printf("RX,%d,%d,%d,%u,%u,%d,%ld,%ld\n", via, hops, r->vehicle, r->seq,
         r->peak_mg, r->severity, (long)r->lat_e6, (long)r->lon_e6);
}

static void
gateway_rx(struct simple_udp_connection *c, const uip_ipaddr_t *src,
           uint16_t sport, const uip_ipaddr_t *dst, uint16_t dport,
           const uint8_t *data, uint16_t len)
{
  struct aggregate a;
  int i, hops = uip_ds6_if.cur_hop_limit - IP_BUF->ttl + 1;
  if(len > sizeof(a)) {
    return;
  }
  memcpy(&a, data, len);
  for(i = 0; i < a.count && i < RECS_PER_FRAME; i++) {
    /* +1: the vehicle's own broadcast hop to the gateway. */
    print_record(a.gateway, hops + 1, &a.rec[i]);
  }
}

/* A vehicle driving past the sink is heard directly. */
static void
vehicle_rx(struct simple_udp_connection *c, const uip_ipaddr_t *src,
           uint16_t sport, const uip_ipaddr_t *dst, uint16_t dport,
           const uint8_t *data, uint16_t len)
{
  struct report r;
  if(len == sizeof(r)) {
    memcpy(&r, data, len);
    print_record(node_id, 1, &r);
  }
}

PROCESS(sink_process, "Pothole sink");
AUTOSTART_PROCESSES(&sink_process);

PROCESS_THREAD(sink_process, ev, data)
{
  static struct etimer et;
  static uip_ipaddr_t addr;
  rpl_dag_t *dag;
  PROCESS_BEGIN();

  uip_ip6addr(&addr, 0xaaaa, 0, 0, 0, 0, 0, 0, 0);
  uip_ds6_set_addr_iid(&addr, &uip_lladdr);
  uip_ds6_addr_add(&addr, 0, ADDR_AUTOCONF);
  dag = rpl_set_root(RPL_DEFAULT_INSTANCE, &addr);
  if(dag != NULL) {
    uip_ip6addr(&addr, 0xaaaa, 0, 0, 0, 0, 0, 0, 0);
    rpl_set_prefix(dag, &addr, 64);
  }
  /* The sink is mains powered: keep its radio on. */
  NETSTACK_MAC.off(1);

  simple_udp_register(&gw_conn, SINK_PORT, NULL, SINK_PORT, gateway_rx);
  simple_udp_register(&veh_conn, VEHICLE_PORT, NULL, VEHICLE_PORT, vehicle_rx);
  printf("BOOT,sink,%d\n", node_id);

  etimer_set(&et, 30 * CLOCK_SECOND);
  while(1) {
    PROCESS_WAIT_UNTIL(etimer_expired(&et));
    etimer_reset(&et);
    log_energy(node_id);
  }
  PROCESS_END();
}
