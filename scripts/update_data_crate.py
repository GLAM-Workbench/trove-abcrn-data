# Use this to update an existing RO-Crate file generated from a 
# GLAM Workbench notebook repository (using the --data-repo option)
# If there are new datafiles, you'll need to regenerate the RO-Crate from the
# notebook repo.

import argparse
from frictionless import describe, Resource, Detector
from pathlib import Path
import datetime
from rocrate.rocrate import ROCrate, ContextEntity
import os

schema_props = {
    "@type" :["File"],
    "encodingFormat":  "application/json",
    "conformsTo": {"@id" : "https://specs.frictionlessdata.io/table-schema/"}  
}

def add_update_action(crate, version):
    """
    Adds an UpdateAction to the crate when the repo version is updated.
    """
    # Create an id for the action using the version number
    action_id = f"create_version_{version.replace('.', '_')}"

    # Set basic properties for action
    properties = {
        "@type": "UpdateAction",
        "endDate": datetime.datetime.now().strftime("%Y-%m-%d"),
        "name": f"Create version {version}",
        "actionStatus": {"@id": "http://schema.org/CompletedActionStatus"},
    }

    # Create entity
    crate.add(ContextEntity(crate, action_id, properties=properties))

def get_create_action(crate, datafile):
    actions = crate.get_by_type("CreateAction")
    for action in actions:
        props = action.properties()
        for result in props["result"]:
            if result["@id"] == datafile:
                return action

def check_schema(file_path):
    schema_name = Path(f"{file_path.with_suffix('').name}-schema.json")
    if schema_name.exists():
        resource = Resource(file_path, schema=str(schema_name))
        report = resource.validate()
        if not report.valid:
            print(f"Validation failed: {file_path}")
            print(report)
        #print(report)
    else:
        detector = Detector(sample_size=1000)
        schema = describe(file_path.name, type='schema', detector=detector)
        schema.to_json(schema_name)
    return schema_name

def main(version):
    os.chdir(Path(__file__).resolve().parent.parent)
    crate = ROCrate("./")
    for datafile in crate.get_by_type(["File", "Dataset"]):
        data_props = datafile.properties()
        file_path = Path(data_props["name"])

        # Update file stats
        stats = file_path.stat()
        date_modified = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d")
        data_props.update({"contentSize": stats.st_size, "dateModified": date_modified})

        # Add/update schema
        if datafile.get("encodingFormat") == "text/csv":
            schema_name = check_schema(file_path)
            data_props.update({"conformsTo": {"@id": str(schema_name)}})
            schema_props["name"] = f"Frictionless Table Schema for {data_props['name']} dataset"
            crate.add_file(str(schema_name), properties=schema_props)

        # Update CreateAction
        action = get_create_action(crate, str(file_path))
        action.properties().update({"endDate": date_modified})

    # Update version
    if version:
        crate.update_jsonld(
            {
                "@id": "./",
                "version": version,
                "datePublished": datetime.datetime.now().strftime("%Y-%m-%d"),
            }
        )
        add_update_action(crate, version)
    crate.write("./")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", type=str, help="New version number", required=False
    )
    args = parser.parse_args()
    main(args.version)
