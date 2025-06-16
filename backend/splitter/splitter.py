import pandas as pd
import re
from pm4py.objects.ocel.obj import OCEL

from .utils import read_ocel_from_json


class Splitter:

    def _read_ocel_object(self, ocel_object: dict) -> OCEL:
        parameters = {
            "encoding": "utf-8",
        }
        log = read_ocel_from_json(ocel_object, parameters=parameters)
        return log

    def transform_ocel(
        self, ocel, custom=False, create_object_relations=False, lead_object_type=None
    ):
        # Function to clean names: strip non-alphanumerical characters and spaces, capitalize first letter of each word
        def clean_name(name):
            name = re.sub(r"[^0-9a-zA-Z ]+", "", name)
            name = " ".join(word.capitalize() for word in name.split())
            name = name.replace(" ", "")
            return name

        # Prepare collections
        object_dataframes = {}
        event_dataframes = {}
        relationship_dataframes = {}

        # Get unique object types and event types
        object_types = ocel.objects["ocel:type"].unique()
        event_types = ocel.events["ocel:activity"].unique()

        # Process objects for each object type
        for obj_type in object_types:
            # Clean object type name
            df_name = clean_name(obj_type)
            # Filter objects of this type
            obj_df = ocel.objects[ocel.objects["ocel:type"] == obj_type].copy()
            # Remove columns starting with 'ocel:'
            additional_columns = [
                col for col in obj_df.columns if not col.startswith("ocel:")
            ]
            # Keep columns where at least one object has a non-null value
            cols_with_values = [
                col for col in additional_columns if obj_df[col].notnull().any()
            ]
            # Select ID column and additional columns
            columns_to_keep = ["ocel:oid"] + cols_with_values
            obj_df = obj_df[columns_to_keep]
            # Rename 'ocel:oid' to 'ID'
            obj_df.rename(columns={"ocel:oid": "ID"}, inplace=True)
            new_columns = {x: clean_name(x) for x in obj_df.columns}
            new_columns["ID"] = "ID"
            obj_df.rename(columns=new_columns, inplace=True)
            # Add to the collection
            object_dataframes[df_name] = obj_df

        # Process events for each event type
        for evt_type in event_types:
            # Clean event type name
            df_name = clean_name(evt_type)
            # Filter events of this type
            evt_df = ocel.events[ocel.events["ocel:activity"] == evt_type].copy()
            # Remove columns starting with 'ocel:'
            additional_columns = [
                col for col in evt_df.columns if not col.startswith("ocel:")
            ]
            # Keep columns where at least one event has a non-null value
            cols_with_values = [
                col for col in additional_columns if evt_df[col].notnull().any()
            ]
            # Select ID column, Time column, and additional columns
            columns_to_keep = ["ocel:eid", "ocel:timestamp"] + cols_with_values
            evt_df = evt_df[columns_to_keep]
            # Rename 'ocel:eid' to 'ID', 'ocel:timestamp' to 'Time'
            evt_df.rename(
                columns={"ocel:eid": "ID", "ocel:timestamp": "Time"}, inplace=True
            )
            new_columns = {x: clean_name(x) for x in evt_df.columns}
            new_columns["ID"] = "ID"
            evt_df.rename(columns=new_columns, inplace=True)
            # Add to the collection
            event_dataframes[df_name] = evt_df

        # Process relationships between events and objects
        relations_df = ocel.relations
        # Get unique pairs of (event type, object type)
        event_object_pairs = relations_df[
            ["ocel:activity", "ocel:type"]
        ].drop_duplicates()
        for idx, row in event_object_pairs.iterrows():
            evt_type = row["ocel:activity"]
            obj_type = row["ocel:type"]
            # Clean names
            evt_name = clean_name(evt_type)
            obj_name = clean_name(obj_type)

            # Filter relations for this pair
            rel_df = relations_df[
                (relations_df["ocel:activity"] == evt_type)
                & (relations_df["ocel:type"] == obj_type)
            ]

            # Check if each event of this event type is related to exactly one object of this object type
            counts = rel_df.groupby("ocel:eid")["ocel:oid"].nunique()
            if counts.eq(1).all():
                # Map from event ID to object ID
                eid_to_oid = rel_df.set_index("ocel:eid")["ocel:oid"]
                # Get the event dataframe
                evt_df = event_dataframes[evt_name]
                # Map event IDs to object IDs
                if custom:
                    this_c_name = obj_name
                else:
                    this_c_name = obj_name
                evt_df[this_c_name] = evt_df["ID"].map(eid_to_oid)
                # Update the event dataframe in the collection
                event_dataframes[evt_name] = evt_df
            else:
                # Create a dataframe for this (event type, object type) pair
                # Columns should be 'ID' (object ID), 'EventID' (event ID)
                pair_df = rel_df[["ocel:oid", "ocel:eid"]].copy()
                if custom:
                    pair_df.rename(
                        columns={"ocel:eid": "ID", "ocel:oid": obj_name}, inplace=True
                    )
                else:
                    pair_df.rename(
                        columns={"ocel:oid": "ID", "ocel:eid": "EventID"}, inplace=True
                    )
                # Store under key (evt_name, obj_name)
                key = (evt_name, obj_name)
                relationship_dataframes[key] = pair_df

        # Process object-to-object relationships if the flag is set
        if create_object_relations and lead_object_type is not None:
            object_relationship_dataframes = {}

            lead_obj_name = clean_name(lead_object_type)

            # Filter relations to get lead object type relations
            lead_relations = ocel.relations[
                ocel.relations["ocel:type"] == lead_object_type
            ].rename(columns={"ocel:oid": "LeadObjectID"})

            # Filter relations to get other object types
            other_relations = ocel.relations[
                ocel.relations["ocel:type"] != lead_object_type
            ].rename(columns={"ocel:oid": "OtherObjectID"})

            # Merge on event ID to find object-to-object relations
            merged_relations = pd.merge(
                lead_relations[["ocel:eid", "LeadObjectID"]],
                other_relations[["ocel:eid", "OtherObjectID", "ocel:type"]],
                on="ocel:eid",
            )

            # For each other object type
            for obj_type in merged_relations["ocel:type"].unique():
                # child_obj_name = clean_name(obj_type) #! original script unused variable

                obj_type_relations = merged_relations[
                    merged_relations["ocel:type"] == obj_type
                ]

                # Check if each child object is related to exactly one lead object
                counts = obj_type_relations.groupby("OtherObjectID")[
                    "LeadObjectID"
                ].nunique()
                if counts.eq(1).all():
                    # Map from child object ID to parent object ID
                    mapping = (
                        obj_type_relations[["OtherObjectID", "LeadObjectID"]]
                        .drop_duplicates()
                        .set_index("OtherObjectID")["LeadObjectID"]
                    )

                    # Get the object dataframe
                    obj_df_name = clean_name(obj_type)
                    obj_df = object_dataframes[obj_df_name]

                    # Add parent object column
                    parent_col_name = clean_name(lead_object_type)
                    obj_df[parent_col_name] = obj_df["ID"].map(mapping)

                    # Update the object dataframe
                    object_dataframes[obj_df_name] = obj_df
                else:
                    # Create object relationship dataframe
                    rel_df = obj_type_relations[
                        ["LeadObjectID", "OtherObjectID"]
                    ].rename(
                        columns={"LeadObjectID": lead_obj_name, "OtherObjectID": "ID"}
                    )
                    parent_name = clean_name(lead_object_type)
                    child_name = clean_name(obj_type)
                    key = f"{parent_name}_{child_name}_objrelations"
                    object_relationship_dataframes[key] = rel_df
        else:
            object_relationship_dataframes = {}

        return (
            object_dataframes,
            event_dataframes,
            relationship_dataframes,
            object_relationship_dataframes,
        )

    def dataframe_to_sql_chunks(self, df: pd.DataFrame) -> list[str]:
        """
        Convert every row of `df` to a `SELECT … FROM (SELECT 1)` block, then
        group up to a dynamic number of those blocks together with `UNION ALL`.

        The chunk size is determined by the number of columns:
        - 1-2 columns: 1000 rows per chunk
        - 3 columns: 500 rows per chunk
        - 4 columns: 250 rows per chunk
        - 5 columns: 125 rows per chunk
        - 6 columns: 60 rows per chunk
        - 7 columns: 30 rows per chunk
        - 8+ columns: 20 rows per chunk

        Parameters
        ----------
        df : pd.DataFrame

        Returns
        -------
        list[str]
            Each element contains SELECT statements separated by `UNION ALL`.
            If the DataFrame is empty, the list is empty.
        """
        # Determine dynamic chunk_size based on number of columns
        max_parts = len(df.columns)
        if max_parts <= 2:
            chunk_size = 1000
        elif max_parts == 3:
            chunk_size = 500
        elif max_parts == 4:
            chunk_size = 250
        elif max_parts == 5:
            chunk_size = 125
        elif max_parts == 6:
            chunk_size = 60
        elif max_parts == 7:
            chunk_size = 30
        else:  # 8 or more
            chunk_size = 20

        select_lines: list[str] = []

        for _, row in df.iterrows():
            parts = []
            for col_name, value in row.items():
                if pd.isnull(value):
                    value_sql = "NULL"
                elif isinstance(value, pd.Timestamp):
                    value_sql = f"TIMESTAMP '{value.strftime('%Y-%m-%d %H:%M:%S')}'"
                elif isinstance(value, (int, float)):
                    value_sql = str(value)
                else:
                    # escape single quotes by doubling them
                    value_sql = "'" + str(value).replace("'", "''") + "'"

                parts.append(f'{value_sql} AS "{col_name}"')

            select_lines.append(
                "SELECT\n\t"
                + ",\n\t".join(parts)
                + "\nFROM (SELECT 1) AS dummy\nWHERE 1=1"
            )

        # pack into ≤ chunk_size-sized groups
        return [
            "\n\nUNION ALL\n\n".join(select_lines[i : i + chunk_size])
            for i in range(0, len(select_lines), chunk_size)
        ]

    def split(self, ocel_object: dict) -> tuple[
        dict[str, list[str]],
        dict[str, list[str]],
        dict[str, list[str]],
        dict[str, list[str]],
    ]:
        ocel = self._read_ocel_object(ocel_object)

        # Set the flag and specify the lead object type
        create_object_relations = True
        lead_object_type = "Container"

        object_dfs, event_dfs, relationship_dfs, object_relationship_dfs = (
            self.transform_ocel(
                ocel,
                custom=True,
                create_object_relations=create_object_relations,
                lead_object_type=lead_object_type,
            )
        )

        objects_sql = {}
        events_sql = {}
        relationships_sql = {}
        object_relationships_sql = {}

        for ot, objs in object_dfs.items():
            objects_sql[ot] = self.dataframe_to_sql_chunks(objs)

        for et, evs in event_dfs.items():
            events_sql[et] = self.dataframe_to_sql_chunks(evs)

        for (evt_name, obj_name), rel in relationship_dfs.items():
            relationships_sql[f"{evt_name}_{obj_name}_relations"] = (
                self.dataframe_to_sql_chunks(rel)
            )

        for rel_name, rel_df in object_relationship_dfs.items():
            object_relationships_sql[rel_name] = self.dataframe_to_sql_chunks(rel_df)

        return objects_sql, events_sql, relationships_sql, object_relationships_sql
