# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# (c) 2025 Ravi Natarajan. All rights reserved.

"""
XML <-> JSON Data Transformers
------------------------------
Out-of-box data transformers implementing bidirectional conversion
between XML and JSON formats for K9-AIF utility use.

Classes:
    - JsonToXmlDataTransformer -> JSON -> XML
    - XmlToJsonDataTransformer -> XML -> JSON
"""

import json
import xmltodict
import dicttoxml


class _BaseDataTransformer:
    """
    Minimal local base class for transformation utilities.

    This avoids coupling these helpers to an unavailable framework
    base class while preserving a common interface.
    """

    def log_trace(self, message: str) -> None:
        print(f"[{self.__class__.__name__}] {message}")

    def transform(self, data, **kwargs):
        raise NotImplementedError

    def validate(self, data):
        raise NotImplementedError


class JsonToXmlDataTransformer(_BaseDataTransformer):
    """Converts JSON/dict input to XML format."""

    def transform(self, data, **kwargs):
        self.log_trace("Starting JSON->XML transformation.")
        try:
            xml_bytes = dicttoxml.dicttoxml(data, attr_type=False, custom_root="root")
            xml_str = xml_bytes.decode("utf-8")

            if not xml_str.strip():
                raise ValueError("Empty XML transformation output.")

            self.log_trace(f"Transformation complete. Output size: {len(xml_str)} chars.")
            return xml_str

        except Exception as ex:
            self.log_trace(f"Error during JSON->XML transformation: {ex}")
            raise

    def validate(self, data):
        """Basic validation: XML output must begin with '<'."""
        valid = isinstance(data, str) and data.strip().startswith("<")
        if not valid:
            self.log_trace("Validation failed: Invalid XML output.")
        return valid


class XmlToJsonDataTransformer(_BaseDataTransformer):
    """Converts XML input to JSON/dict format."""

    def transform(self, xml_input: str, **kwargs):
        self.log_trace("Starting XML->JSON transformation.")
        try:
            parsed = xmltodict.parse(xml_input)
            json_data = json.loads(json.dumps(parsed))

            if not isinstance(json_data, dict):
                raise ValueError("Parsed JSON is not a dictionary.")

            self.log_trace(f"Transformation complete. Keys: {len(json_data.keys())}")
            return json_data

        except Exception as ex:
            self.log_trace(f"Error during XML->JSON transformation: {ex}")
            raise

    def validate(self, data):
        """Basic validation: output must be a non-empty dict."""
        valid = isinstance(data, dict) and bool(data)
        if not valid:
            self.log_trace("Validation failed: Empty or invalid JSON data.")
        return valid