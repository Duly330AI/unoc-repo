Objective: Fully Integrate the CORE_SITE Container into the Application.
Context: We have successfully implemented the AONSwitchCockpit. The final step to complete the container feature is to make the CORE_SITE container fully creatable and functional, just like the POP.
Instructions:
Part 1: Backend - Create a Default Hardware Model for CORE_SITE
Action: In backend/services/seed_service.py, within the ensure_default_hardware_models() function, you must now also create a default HardwareModel for the DeviceType.CORE_SITE.
Details:
Model Name: "Generic Core Site"
This model should define a sensible number of slots (e.g., 3-5) for core equipment. You can reference the docs/container-layouts.json for the slot coordinates.
Part 2: Frontend - Add CORE_SITE to the Device Palette
Action: In unoc-frontend-v2/src/components/palette/DevicePalette.vue, add a new draggable entry for CORE_SITE.
Details:
Place it in the ZENTRALE & POP (CONTAINER) section, directly below the existing POP entry.
Verification:
After the changes, confirm that a new "CORE_SITE" entry appears in the device palette.
Drag the CORE_SITE onto the canvas.
Confirm that the "Hardware auswählen" modal appears and correctly shows the new "Generic Core Site" model.
Create the CORE_SITE container and confirm that it renders correctly on the canvas.
Confirm that you can successfully drag and snap a CORE_ROUTER into one of its slots.
