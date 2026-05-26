from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.schema_constraints_builder import SchemaConstraintsBuilder


class SchemaConstraintsTest(unittest.TestCase):
    def test_structured_output_schema_is_strict_object_shape(self) -> None:
        schema = SchemaConstraintsBuilder().structured_output_schema(evidence_names=["evidence_a", "evidence_b"])
        object_nodes = self._object_nodes(schema)
        self.assertGreater(len(object_nodes), 10)
        for node in object_nodes:
            self.assertIs(node.get("additionalProperties"), False)
            properties = node.get("properties") or {}
            self.assertEqual(set(node.get("required") or []), set(properties))

    def test_material_evidence_source_uses_dynamic_enum(self) -> None:
        schema = SchemaConstraintsBuilder().structured_output_schema(evidence_names=["evidence_a", "evidence_b"])
        evidence_source = (
            schema["properties"]["mission"]["properties"]["materials"]["items"]["properties"]["evidence_source"]
        )
        self.assertEqual(evidence_source["items"]["enum"], ["evidence_a", "evidence_b"])

    def test_scenario_glossary_is_required_but_can_be_empty(self) -> None:
        schema = SchemaConstraintsBuilder().structured_output_schema(evidence_names=["evidence_a"])
        scenario = schema["properties"]["mission"]["properties"]["scenario"]
        glossary = scenario["properties"]["glossary"]

        self.assertIn("glossary", scenario["required"])
        self.assertEqual(glossary["type"], "array")
        self.assertEqual(set(glossary["items"]["required"]), {"term", "definition"})
        self.assertFalse(glossary["items"]["additionalProperties"])

    def _object_nodes(self, node: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        if isinstance(node, dict):
            if node.get("type") == "object":
                found.append(node)
            for value in node.values():
                found.extend(self._object_nodes(value))
        elif isinstance(node, list):
            for value in node:
                found.extend(self._object_nodes(value))
        return found


if __name__ == "__main__":
    unittest.main()
