# Vehicle firmware: IPv6 host, RPL deliberately compiled out.
all: vehicle
CONTIKI = ../../..
CFLAGS += -DPROJECT_CONF_H=\"project-conf.h\"
CONTIKI_WITH_IPV6 = 1
CONTIKI_WITH_RPL = 0
include $(CONTIKI)/Makefile.include
