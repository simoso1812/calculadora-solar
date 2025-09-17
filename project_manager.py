"""
Project Management System for Solar Calculator
Handles project storage, retrieval, and management via Google Sheets
"""

import os
import json
import datetime
from typing import Dict, List, Any, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import pandas as pd

class ProjectManager:
    """
    Manages solar projects with Google Sheets integration
    """

    def __init__(self):
        self.service = None
        self.spreadsheet_id = None
        self._initialize_sheets_service()

    def _initialize_sheets_service(self):
        """Initialize Google Sheets service"""
        try:
            creds = Credentials(
                None,
                refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=os.environ.get("GOOGLE_CLIENT_ID"),
                client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
                scopes=['https://www.googleapis.com/auth/spreadsheets',
                       'https://www.googleapis.com/auth/drive']
            )
            self.service = build('sheets', 'v4', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)

            # Get or create spreadsheet
            self.spreadsheet_id = os.environ.get("PROJECTS_SPREADSHEET_ID")
            if not self.spreadsheet_id:
                self._create_projects_spreadsheet()

            # Check parent folder access
            self._check_parent_folder_access()

        except Exception as e:
            print(f"Error initializing Google Sheets: {e}")
            self.service = None

    def _check_parent_folder_access(self):
        """Check if we can access the parent folder, provide fallback if not"""
        parent_folder_id = os.environ.get('PARENT_FOLDER_ID')

        if not parent_folder_id:
            print("No PARENT_FOLDER_ID specified - Google Drive folder operations will be limited")
            self.parent_folder_accessible = False
            return

        try:
            # Try to access the folder
            folder = self.drive_service.files().get(
                fileId=parent_folder_id,
                fields='name, id'
            ).execute()

            print(f"Parent folder accessible: {folder.get('name')}")
            self.parent_folder_accessible = True

        except Exception as e:
            print(f"Cannot access parent folder {parent_folder_id}: {e}")
            print("This is normal if the folder was created with different OAuth credentials")
            print("The app will work with limited Google Drive functionality")
            print("You can still save/load projects and generate financial summaries")
            self.parent_folder_accessible = False

    def _create_projects_spreadsheet(self):
        """Create a new spreadsheet for projects"""
        try:
            spreadsheet = {
                'properties': {
                    'title': 'Solar Calculator Projects',
                    'locale': 'es_CO'
                },
                'sheets': [
                    {'properties': {'title': 'Projects'}},
                    {'properties': {'title': 'Scenarios'}},
                    {'properties': {'title': 'Calculations'}}
                ]
            }

            spreadsheet = self.service.spreadsheets().create(
                body=spreadsheet, fields='spreadsheetId'
            ).execute()

            self.spreadsheet_id = spreadsheet.get('spreadsheetId')

            # Set up headers
            self._setup_sheet_headers()

            # Store spreadsheet ID in environment for future use
            print(f"Created new projects spreadsheet: {self.spreadsheet_id}")

        except Exception as e:
            print(f"Error creating spreadsheet: {e}")

    def _setup_sheet_headers(self):
        """Set up headers for all sheets"""
        headers = {
            'Projects': [
                ['Project ID', 'Client Name', 'Project Name', 'Location', 'Created Date',
                 'Last Modified', 'Status', 'Base Calculation ID']
            ],
            'Scenarios': [
                ['Scenario ID', 'Project ID', 'Scenario Name', 'Price Override',
                 'Created Date', 'Financial Metrics', 'Status']
            ],
            'Calculations': [
                ['Calculation ID', 'Project ID', 'Input Data', 'Results Data',
                 'Created Date', 'Version']
            ]
        }

        for sheet_name, header_data in headers.items():
            range_name = f'{sheet_name}!A1'
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': header_data}
            ).execute()

    def save_project(self, project_data: Dict[str, Any]) -> str:
        """
        Save a new project to Google Sheets

        Args:
            project_data: Dictionary containing project information

        Returns:
            Project ID
        """
        if not self.service:
            raise Exception("Google Sheets service not available")

        project_id = f"PRJ{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Prepare project row
        project_row = [
            project_id,
            project_data.get('client_name', ''),
            project_data.get('project_name', ''),
            project_data.get('location', ''),
            datetime.datetime.now().isoformat(),
            datetime.datetime.now().isoformat(),
            'Active',
            project_data.get('base_calculation_id', '')
        ]

        # Append to Projects sheet
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range='Projects!A:A',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [project_row]}
        ).execute()

        return project_id

    def save_calculation(self, project_id: str, input_data: Dict, results_data: Dict) -> str:
        """
        Save calculation data for a project

        Args:
            project_id: Project ID
            input_data: Input parameters
            results_data: Calculation results

        Returns:
            Calculation ID
        """
        if not self.service:
            raise Exception("Google Sheets service not available")

        calculation_id = f"CALC{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Convert data to JSON strings for storage
        input_json = json.dumps(input_data, default=str)
        results_json = json.dumps(results_data, default=str)

        calculation_row = [
            calculation_id,
            project_id,
            input_json,
            results_json,
            datetime.datetime.now().isoformat(),
            '1.0'
        ]

        # Append to Calculations sheet
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range='Calculations!A:A',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [calculation_row]}
        ).execute()

        return calculation_id

    def save_scenario(self, project_id: str, scenario_name: str,
                     price_override: float = None, financial_metrics: Dict = None) -> str:
        """
        Save a price scenario for a project

        Args:
            project_id: Project ID
            scenario_name: Name of the scenario
            price_override: Manual price override
            financial_metrics: Financial calculation results

        Returns:
            Scenario ID
        """
        if not self.service:
            raise Exception("Google Sheets service not available")

        scenario_id = f"SCN{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Convert financial metrics to JSON
        metrics_json = json.dumps(financial_metrics or {}, default=str)

        scenario_row = [
            scenario_id,
            project_id,
            scenario_name,
            str(price_override) if price_override else '',
            datetime.datetime.now().isoformat(),
            metrics_json,
            'Active'
        ]

        # Append to Scenarios sheet
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range='Scenarios!A:A',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [scenario_row]}
        ).execute()

        return scenario_id

    def load_project(self, project_id: str) -> Dict[str, Any]:
        """
        Load project data from Google Sheets

        Args:
            project_id: Project ID to load

        Returns:
            Project data dictionary
        """
        if not self.service:
            raise Exception("Google Sheets service not available")

        # Get all projects
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Projects!A2:H'
        ).execute()

        values = result.get('values', [])
        for row in values:
            if len(row) >= 8 and row[0] == project_id:
                return {
                    'project_id': row[0],
                    'client_name': row[1],
                    'project_name': row[2],
                    'location': row[3],
                    'created_date': row[4],
                    'last_modified': row[5],
                    'status': row[6],
                    'base_calculation_id': row[7]
                }

        raise Exception(f"Project {project_id} not found")

    def load_calculation(self, calculation_id: str) -> Dict[str, Any]:
        """
        Load calculation data from Google Sheets

        Args:
            calculation_id: Calculation ID to load

        Returns:
            Calculation data dictionary
        """
        if not self.service:
            raise Exception("Google Sheets service not available")

        # Get all calculations
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Calculations!A2:F'
        ).execute()

        values = result.get('values', [])
        for row in values:
            if len(row) >= 6 and row[0] == calculation_id:
                return {
                    'calculation_id': row[0],
                    'project_id': row[1],
                    'input_data': json.loads(row[2]) if row[2] else {},
                    'results_data': json.loads(row[3]) if row[3] else {},
                    'created_date': row[4],
                    'version': row[5]
                }

        raise Exception(f"Calculation {calculation_id} not found")

    def get_project_scenarios(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all scenarios for a project

        Args:
            project_id: Project ID

        Returns:
            List of scenario dictionaries
        """
        if not self.service:
            raise Exception("Google Sheets service not available")

        # Get all scenarios
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Scenarios!A2:G'
        ).execute()

        scenarios = []
        values = result.get('values', [])
        for row in values:
            if len(row) >= 7 and row[1] == project_id:
                scenarios.append({
                    'scenario_id': row[0],
                    'project_id': row[1],
                    'scenario_name': row[2],
                    'price_override': float(row[3]) if row[3] else None,
                    'created_date': row[4],
                    'financial_metrics': json.loads(row[5]) if row[5] else {},
                    'status': row[6]
                })

        return scenarios

    def list_projects(self, status_filter: str = None) -> List[Dict[str, Any]]:
        """
        List all projects

        Args:
            status_filter: Filter by status ('Active', 'Archived', etc.)

        Returns:
            List of project dictionaries
        """
        if not self.service:
            raise Exception("Google Sheets service not available")

        # Get all projects
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Projects!A2:H'
        ).execute()

        projects = []
        values = result.get('values', [])
        for row in values:
            if len(row) >= 8:
                project = {
                    'project_id': row[0],
                    'client_name': row[1],
                    'project_name': row[2],
                    'location': row[3],
                    'created_date': row[4],
                    'last_modified': row[5],
                    'status': row[6],
                    'base_calculation_id': row[7]
                }

                if not status_filter or project['status'] == status_filter:
                    projects.append(project)

        return projects

    def update_project_status(self, project_id: str, status: str):
        """
        Update project status

        Args:
            project_id: Project ID
            status: New status
        """
        if not self.service:
            raise Exception("Google Sheets service not available")

        # Find and update the project row
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Projects!A2:H'
        ).execute()

        values = result.get('values', [])
        for i, row in enumerate(values):
            if len(row) >= 8 and row[0] == project_id:
                # Update status and last modified
                row[5] = datetime.datetime.now().isoformat()  # last_modified
                row[6] = status  # status

                # Update the row
                range_name = f'Projects!A{i+2}:H{i+2}'
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body={'values': [row]}
                ).execute()
                break

    def export_project_data(self, project_id: str) -> Dict[str, Any]:
        """
        Export complete project data including all scenarios and calculations

        Args:
            project_id: Project ID

        Returns:
            Complete project data dictionary
        """
        project = self.load_project(project_id)
        scenarios = self.get_project_scenarios(project_id)

        # Load base calculation if exists
        base_calculation = None
        if project.get('base_calculation_id'):
            try:
                base_calculation = self.load_calculation(project['base_calculation_id'])
            except:
                base_calculation = None

        return {
            'project': project,
            'base_calculation': base_calculation,
            'scenarios': scenarios,
            'export_date': datetime.datetime.now().isoformat()
        }

# Global instance
project_manager = ProjectManager()