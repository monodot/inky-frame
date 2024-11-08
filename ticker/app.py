import os
import json
import requests
import boto3
import socket
import platform
import getpass
from datetime import datetime, timedelta
from typing import Dict, List, Any


def transform_data(data: Dict[str, Any], project_filter: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Transform GitHub GraphQL response into desired format.

    Args:
        data: Raw GraphQL response
        project_filter: Project title to filter by (e.g. "My Team Project")

    Returns:
        Dict of issues grouped by status
    """
    # First, filter the nodes
    filtered_nodes = []

    for node in data["data"]["user"]["issues"]["nodes"]:
        # Check if any project matches our criteria
        for project_node in node["projects"]["nodes"]:
            project_title = project_node.get("project", {}).get("title")
            sprint_title = project_node.get("sprint", {}).get(
                "title") if project_node.get("sprint") else None

            if project_title == project_filter and sprint_title is not None:
                hours = project_node.get("hours")
                hours_value = hours.get(
                    "number") if hours is not None else None

                # Transform the node
                transformed_node = {
                    "title": node["title"],
                    "sprint": project_node.get("sprint", {}).get("title"),
                    "status": project_node.get("status", {}).get("value"),
                    "hours": hours_value,
                    "project": project_node.get("project", {}).get("title"),
                    "activity": project_node.get("activity", {}).get("value")
                }
                filtered_nodes.append(transformed_node)
                break  # Found a matching project, no need to check others

    # Group by status
    grouped_nodes = {}
    for node in filtered_nodes:
        status = node["status"]
        if status not in grouped_nodes:
            grouped_nodes[status] = []
        grouped_nodes[status].append(node)

    return grouped_nodes


def load_query(filename="github_issues_work.graphql"):
    """Load GraphQL query from file"""
    with open(filename, 'r') as f:
        return f.read()


def main():
    # GitHub API configuration
    token = os.environ["GITHUB_TOKEN"]
    project_filter = os.environ.get("FRAME_PROJECT_FILTER", "My Team Project")

    two_weeks_ago = (datetime.utcnow() - timedelta(weeks=2)).isoformat() + "Z"

    query = load_query()
    variables = {
        "login": "monodot",
        "since": two_weeks_ago
    }

    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url,
        headers=headers,
        json={
            "query": query,
            "variables": variables
        }
    )
    response.raise_for_status()
    raw_data = response.json()

    with open("github_raw_response.json", "w") as f:
        json.dump(raw_data, f, indent=2)
    print(f"Raw GitHub response saved to github_raw_response.json")

    transformed_data = transform_data(raw_data, project_filter)

    # Create our simplified issues structure
    output = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",  # UTC time with Z suffix
            "hostname": socket.gethostname(),
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "user": getpass.getuser(),
            },
        },
        "data": transformed_data
    }

    # Write to local file
    with open("work.json", "w") as f:
        json.dump(output, f, indent=2)

    # Upload to S3
    s3 = boto3.client('s3')
    s3.upload_file(
        'work.json',
        'monodot-data',
        'work.json'
    )

    print("Successfully uploaded work file to S3")


if __name__ == "__main__":
    main()
