# Data Model

Key tables: devices, interfaces, links, hardware_models, port_profiles, tariffs, events.

Indexes (must-have):

- links(end_a_id), links(end_b_id)
- interfaces(device_id, role)
- devices(type, parent_container_id)
- port_profiles(hardware_model_id)
