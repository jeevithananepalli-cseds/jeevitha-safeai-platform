"""Domain entities — objects with identity and lifecycle business rules.

Entities (``User``, ``EmergencyContact``, ``EmergencyEvent``, …) are introduced
per the development roadmap (Phase 2+). They are plain Python with their
invariants enforced in-class — e.g. an event's status may only follow valid
transitions. No framework imports belong here.
"""
