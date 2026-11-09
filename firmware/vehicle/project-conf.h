#ifndef PROJECT_CONF_H_
#define PROJECT_CONF_H_

/* Per-state time accounting: the source of the energy metrics. */
#undef  ENERGEST_CONF_ON
#define ENERGEST_CONF_ON 1

/* Tuned for 10 KB RAM on the Tmote Sky. */
#undef  UIP_CONF_TCP
#define UIP_CONF_TCP 0
#undef  NBR_TABLE_CONF_MAX_NEIGHBORS
#define NBR_TABLE_CONF_MAX_NEIGHBORS 16
#undef  UIP_CONF_MAX_ROUTES
#define UIP_CONF_MAX_ROUTES 8
#undef  SICSLOWPAN_CONF_FRAG
#define SICSLOWPAN_CONF_FRAG 0
#undef  UIP_CONF_BUFFER_SIZE
#define UIP_CONF_BUFFER_SIZE 160

/* Vehicles are hosts: no routing, no router advertisements. */
#undef  UIP_CONF_ROUTER
#define UIP_CONF_ROUTER 0

#endif
