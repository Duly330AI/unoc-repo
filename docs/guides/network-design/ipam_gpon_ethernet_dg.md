Topologieüberblick
Code
[Backbone/MPLS]
|
(L3)
[Core Router]
/ \
 (L3) (L3)
[Edge] [AON L3-Switch]
| |
GPON OLT AON-Access
| |
[ONT/NT] [CPE]
IP-Plan backbone, core, edge
Segment Zweck Subnetz Hinweise
Backbone ↔ Core L3-Uplink 172.16.0.0/31 /31 P2P; alternativ /30
Core ↔ Edge L3-Uplink 172.16.0.2/31 deterministisches ECMP möglich
Core ↔ AON L3-Switch L3-Uplink 172.16.0.4/31 nur nötig, wenn AON L3 spricht
Core Loopback Routing-ID 10.255.0.1/32 iBGP/OSPF/IS-IS Router-ID
Edge Loopback BNG/Services 10.255.0.2/32 DHCP-Relay, AAA, BNG
AON L3-Switch Loopback mgmt/routing 10.255.0.3/32 nur falls L3 im Access
IGP: OSPF Area 0 oder IS-IS L2 für Core/Edge/Aggregation.

BGP: iBGP zwischen Core/Edge (Loopbacks), eBGP zur Upstream/Peering, optional BGP-LU für MPLS.

Services: Edge als BNG/BRAS (PPPoE) oder IPoE (DHCP), NAT/CGNAT optional.

Management- und OAM-Netze
Zweck VLAN Subnetz Geräte
OLT Mgmt 900 10.250.0.0/24 OLT-Controller, OLT-Shelf
ONT/NT Mgmt (TR–069) 901 10.250.1.0/24 ONT/NT via ACS
AON/Access Mgmt 902 10.250.2.0/24 AON-Switches
CPE Mgmt (TR–069) 903 10.250.3.0/24 CPE/Residential GW
NOC Jump/Tools 910 10.250.10.0/24 NMS, Syslog, TACACS, ACS
Best Practice: Management in eigene VRF (z. B. VRF mgmt), kein Transit ins Kundendatenpfad, nur NOC—Ingress.

Zugriff: ACLs eng, SSH/SNMP/NETCONF nur aus NOC-Netzen, Syslog/Telemetry out-only.

GPON-Zweig (OLT → ONT → CPE)
VLAN- und Service-Design
Internet (Retail): VLAN 300, IPoE (DHCP) oder PPPoE (je nach Ausbauregion/Wholesale).

IPTV (optional): VLAN 600, Multicast via IGMP Proxy/Snooping.

VoIP (optional): VLAN 700, SIP/RTP priorisiert (DSCP EF).

Kunden—Spezial (Business): VLAN 350–399 (pro Kunde), L2TPv3/VPLS/VRF—Mapped.

Interface VLAN IP/Subnetz Rolle
Edge .300 300 100.64.0.1/24 Gateway CGNAT/BNG (Internet)
Edge .600 600 10.200.0.1/24 IPTV GW/Multicast
Edge .700 700 10.210.0.1/24 VoIP Signalisierung
Edge .900 900 10.250.0.1/24 OLT Mgmt SVI
Adressierung Kunden-Internet:

Privat via CGNAT: 100.64.0.0/10 (z. B. 100.64.0.0/24 je PoP)

Öffentlich: Aggregat /22–/24 am Edge, Kundennetze via DHCP/PPPoE Framed-Route.

Verkehrsfluss GPON
Daten: ONT taggt Internet—VLAN 300 → Edge—BNG terminiert IPoE/PPPoE → Policy (QoS, NAT/CGNAT) → Core/Backbone.

IPTV/VoIP: Separate VLANs mit QoS—Marking, IGMP—Querier am Edge, Multicast aus Core.

Management: OLT/ONT in Mgmt—VRF; TR–069/ACS über VRF—mgmt only.

AON-Zweig (AON L3—Switch → CPE Ethernet)
VLAN— und Service—Design
Internet (Retail): VLAN 400, IPoE (DHCP) oder PPPoE am Edge/BNG.

Business L2 Circuit: VLAN 450–499 je Kunde (QinQ möglich).

Management: VLAN 902 am AON—Switch für Out—of—Band.

Interface VLAN IP/Subnetz Rolle
AON L3-SVI .400 400 100.65.0.1/24 GW Access (optional, wenn L3 am Access)
Edge .400 400 100.65.0.254/24 GW/BNG (wenn L3 nur am Edge)
AON .902 902 10.250.2.1/24 Switch Mgmt
Variante 1 (empfohlen): L2—Only im Access; Edge terminiert VLAN 400 (BNG).

Variante 2: L3 im Access (SVI .400), Default—Route zum Core/Edge, DHCP—Relay → Edge/BNG.

Verkehrsfluss AON
CPE tagged Internet—VLAN 400 → Trunk bis Edge → BNG/Policy → Core/Backbone.

Business L2: VLAN—per—Kunde bis Edge/PE, Mapping in VRF/VPWS/VPLS.

Routing, AAA, QoS
BNG/Subscriber:

IPoE: DHCP Option82 (Access—ID), AAA via RADIUS (Policy/NAT/Public—IP Zuweisung).

PPPoE: RADIUS (Framed—IP/Route, QoS—Profile), Session—Limits, Idle—Timeout.

QoS:

Marking: DSCP AFxx für IPTV, EF für VoIP, CS0 Best—Effort für Internet.

Shaping/Policing: pro—Subscriber auf dem Edge, Queue—Design für Triple—Play.

Security:

uRPF/BCP38 an Edge—Access—Facing SVIs.

Storm—Control, DHCP—Snooping, ARP—Inspection im Access.

MAC—Limits pro UNI (CPE/ONT Port).

Beispiel—Konfigurationen (plattformneutral)
Edge — SVIs (GPON)
Internet VLAN 300: 100.64.0.1/24 (BNG/NAT)

IPTV VLAN 600: 10.200.0.1/24 (IGMP Querier)

VoIP VLAN 700: 10.210.0.1/24

Mgmt VLAN 900: 10.250.0.1/24

Core—Edge Links
Core—Edge: 172.16.0.2/31 (Core .2, Edge .3), IGP aktiv

Loopbacks: Core 10.255.0.1/32, Edge 10.255.0.2/32 (iBGP)

Alternative IP—Vorschläge (falls du andere Blöcke brauchst)
P2P—Links: 10.0.0.0/31 ff. oder 192.0.2.0/31 (Dokunetze)

Management—VRF: 172.20.0.0/16 in /24—Slices pro Technologie (OLT/ONT/Switch/CPE)

Kundenpools (CGNAT): 100.64.0.0/17 GPON, 100.64.128.0/17 AON

Öffentliche Aggregation: z. B. 203.0.113.0/24 (Platzhalter) am Edge, via BGP announced

Umsetzungshinweise „wie bei DG“
ONT/NT als Bridge: Kunde/CPE hängt via RJ—45; Services per VLAN getrennt.

TR–069/ACS: Separates Mgmt—VLAN/VRF, kein Mischverkehr.

Service—Modelle: Region/Wholesale entscheidet (IPoE vs PPPoE, VLAN—IDs); Design oben deckt beide Varianten ab, du togglest nur Terminierung (DHCP/PPPoE) am Edge.
