# SPDX-FileCopyrightText: 2024 University of Applied Sciences Osnabrück
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: MIT


class JSONSchemaDefault:
    def __init__(self, schema: dict):
        self.schema = schema
        self.defaults = {}
        properties: dict[str, dict] = self.schema.get("properties", {})
        # Go through Sub-Schemas
        for name, schema in properties.items():
            self.generate_default_values(name, schema)

        # GO through all allOf values and get the ones with the fulfilled constraint
        all_of = self.schema.get("allOf")

        if all_of:
            for s in all_of:
                constrained = False
                for key in s.keys():
                    if key == "if":
                        properties: dict[str, dict] = s[key].get("properties", {})
                        for name, schema in properties.items():
                            for key in schema.keys():
                                if self.defaults[name] == schema[key]:
                                    constrained = True

                    if key == "then" and constrained:
                        constrained = False
                        properties: dict[str, dict] = s[key].get("properties", {})
                        for name, schema in properties.items():
                            if "default" in schema:
                                self.generate_default_values(name, schema)

    def get_default_values(self):
        if self.defaults:
            return self.defaults

    def generate_default_values(self, name, schema):
        default = None
        _type = self.get_type(schema)

        if "default" in schema:
            default = self.defaults[name] = schema["default"]
        elif "enum" in schema:
            default = self.defaults[name] = schema["enum"][0]
        else:
            default = self.defaults[name] = self.get_replacement_value(
                name, schema, _type
            )
        return default

    def get_replacement_value(self, name, schema, _type):
        match _type:
            case "string":
                # If no default is given, set default to empts string
                default = ""
                if "default" in schema:
                    default = schema["default"]
            case "object":
                default = {}
                # create new JSONSchemaDefault for subobjects
                default = JSONSchemaDefault(schema).get_default_values()
            case "array":
                default = []
                # Get Default value in Array, else go through nested arrays
                if "default" in schema:
                    default = schema["default"]
                else:
                    found_default = False
                    for key, value in schema.items():
                        if key == "default":
                            default.append(value)
                            found_default = True
                        elif key == "enum" and not found_default:
                            default.append(value)
                        elif key == "items":
                            if self.generate_default_values(name, value) is not None:
                                default.append(
                                    self.generate_default_values(name, value)
                                )
                        else:
                            pass
            case "integer":
                default = 0
                # Use minimum if no default is given
                if "minimum" in schema:
                    default = schema["minimum"]
            case "boolean":
                # Default boolean is true
                default = True
            case "number":
                default = 0
                # Use minimum if no default is given
                if "minimum" in schema:
                    default = schema["minimum"]
            case None:
                default = None
            case other:
                print("{} is not a known type.".format({schema["type"]}))
                raise RuntimeError("Type unknown.")

        return default

    def get_type(self, schema):
        if "type" in schema:
            _type = schema["type"]
            return _type
