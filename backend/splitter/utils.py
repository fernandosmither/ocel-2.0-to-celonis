"""
This is a modified version of the PM4Py OCEL importer to work with the JSON-OCEL 2 standard format, without a file
-

    PM4Py – A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschränkt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see this software project's root or
visit <https://www.gnu.org/licenses/>.

Website: https://processintelligence.solutions
Contact: info@processintelligence.solutions
"""

from pm4py.objects.ocel.obj import OCEL
from typing import Optional, Dict, Any
from pm4py.objects.ocel.util import filtering_utils
from pm4py.objects.ocel.util import ocel_consistency
from pm4py.objects.ocel.importer.jsonocel.variants import classic
from enum import Enum


class Parameters(Enum):
    ENCODING = "encoding"


def read_ocel_from_json(
    json_obj: dict, parameters: Optional[Dict[Any, Any]] = None
) -> OCEL:
    """
    Imports an OCEL from a JSON-OCEL 2 json object

    Parameters
    --------------
    json_obj
        JSON-OCEL 2 object
        - Parameters.ENCODING

    Returns
    -------------
    ocel
        Object-centric event log
    """
    if parameters is None:
        parameters = {}

    legacy_obj = {}
    legacy_obj["ocel:events"] = {}
    legacy_obj["ocel:objects"] = {}
    legacy_obj["ocel:objectChanges"] = []

    for eve in json_obj["events"]:
        dct = {}
        dct["ocel:activity"] = eve["type"]
        dct["ocel:timestamp"] = eve["time"]
        dct["ocel:vmap"] = {}
        if "attributes" in eve and eve["attributes"]:
            dct["ocel:vmap"] = {x["name"]: x["value"] for x in eve["attributes"]}
        dct["ocel:typedOmap"] = []
        if "relationships" in eve and eve["relationships"]:
            dct["ocel:typedOmap"] = [
                {"ocel:oid": x["objectId"], "ocel:qualifier": x["qualifier"]}
                for x in eve["relationships"]
            ]
        dct["ocel:omap"] = list(set(x["ocel:oid"] for x in dct["ocel:typedOmap"]))
        legacy_obj["ocel:events"][eve["id"]] = dct

    for obj in json_obj["objects"]:
        dct = {}
        dct["ocel:type"] = obj["type"]
        dct["ocel:ovmap"] = {}
        if "attributes" in obj and obj["attributes"]:
            for x in obj["attributes"]:
                if x["name"] in dct["ocel:ovmap"]:
                    legacy_obj["ocel:objectChanges"].append(
                        {
                            "ocel:oid": obj["id"],
                            "ocel:type": obj["type"],
                            "ocel:field": x["name"],
                            x["name"]: x["value"],
                            "ocel:timestamp": x["time"],
                        }
                    )
                else:
                    dct["ocel:ovmap"][x["name"]] = x["value"]
        dct["ocel:o2o"] = []
        if "relationships" in obj and obj["relationships"]:
            dct["ocel:o2o"] = [
                {"ocel:oid": x["objectId"], "ocel:qualifier": x["qualifier"]}
                for x in obj["relationships"]
            ]
        legacy_obj["ocel:objects"][obj["id"]] = dct

    legacy_obj["ocel:global-log"] = {}
    legacy_obj["ocel:global-event"] = {}
    legacy_obj["ocel:global-object"] = {}

    log = classic.get_base_ocel(legacy_obj, parameters=parameters)

    log = ocel_consistency.apply(log, parameters=parameters)

    log = filtering_utils.propagate_relations_filtering(log, parameters=parameters)

    return log
