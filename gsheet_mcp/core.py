import os
from contextlib import asynccontextmanager
from typing import List, AsyncIterator, Optional

from gspread import Client, Worksheet
from gspread.auth import DEFAULT_SERVICE_ACCOUNT_FILENAME
from mcp.server.fastmcp import FastMCP, Context
import gspread

GOOGLE_SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT", DEFAULT_SERVICE_ACCOUNT_FILENAME)


@asynccontextmanager
async def server_lifespan(_server: FastMCP) -> AsyncIterator[Client]:
    """Manage server startup and shutdown lifecycle."""
    # Initialize
    yield gspread.service_account(filename=GOOGLE_SERVICE_ACCOUNT)


mcp_server = FastMCP(
    name="gsheet_mcp",
    lifespan=server_lifespan,
)

def check_skip_empty_row(cell: str) -> bool:
    try:
        return int(cell) != 0 and cell.strip()
    except ValueError:
        return cell.strip() != ""

def sheet_to_markdown(sheet: Worksheet) -> str:
    """
    Convert a 2D list (table data) to a Markdown table.
    """
    table = "First row and column are index, so they are not part of the data.\n"
    table += "Use as a reference to the data index in the sheet.\n"
    table += "If row is empty, it will not show using index as reference\n\n"
    data = sheet.get_values()
    if not data:
        return "Empty sheet, no data to display."
    index_list = [str(i) for i in range(1, len(data[0]))]
    table += "| Index | " + " | ".join(index_list) + " |\n"  # Header row
    for (index, row) in enumerate(data, 1):
        if not any([check_skip_empty_row(cell)  for cell in row ]):  # Skip empty rows
            continue
        table += f"| {index} | " + " | ".join(row) + " |\n"
    return table

@mcp_server.tool()
def list_spreadsheets(ctx: Context):
    """
    List all spreadsheets available in the Google Drive associated with the service account.
    """
    client: Client = ctx.request_context.lifespan_context
    return client.list_spreadsheet_files()


@mcp_server.tool()
def get_sheet(ctx: Context, spreadsheet_id: Optional[str]=None, title: Optional[str]=None):
    """
    Get a spreadsheet info and its sheets details.
    Spreadsheet ID is preferred, but if not provided, it will search by title.
    If both are provided, ID will be used.
    If neither is provided, it will return an error.
    If the spreadsheet is not found, it will return an error.
    Spreadsheet id can be found in the URL of the spreadsheet, e.g.:
        https://docs.google.com/spreadsheets/d/<spreadsheet_id>/....
    Example:
        https://docs.google.com/spreadsheets/d/ef0e1fe3da949be0ce18aec5062c8871abb327a6108b/edit

    Args:
        spreadsheet_id (str, optional): The ID of the spreadsheet. Defaults to None.
        title (str, optional): The title of the spreadsheet. Defaults to None.
    """
    client: Client = ctx.request_context.lifespan_context
    if not spreadsheet_id and not title:
        raise ValueError("Either spreadsheet_id or title must be provided.")
    elif spreadsheet_id:
        spreadsheet = client.open_by_key(spreadsheet_id)
    else:
        spreadsheet = client.open(title=title)
    return {
        "id": spreadsheet.id,
        "title": spreadsheet.title,
        "sheets": [{
            "title": i.title
        } for i in spreadsheet.worksheets()]
    }

@mcp_server.tool()
def read_spreadsheet(
    ctx: Context,
    sheet_name: str,
    spreadsheet_id: Optional[str] = None,
    title: Optional[str] = None
):
    """
    Read data from a spreadsheet.
    If both spreadsheet_id and title are provided, spreadsheet_id will be used.
    If neither is provided, it will return an error.
    If sheet_name is not provided, it will read the first sheet.

    Args:
        spreadsheet_id (str, optional): The ID of the spreadsheet. Defaults to None.
        title (str, optional): The title of the spreadsheet. Defaults to None.
        sheet_name (str): The name of the sheet to read.
    """
    client: Client = ctx.request_context.lifespan_context
    if not spreadsheet_id and not title:
        raise ValueError("Either spreadsheet_id or title must be provided.")
    elif spreadsheet_id:
        spreadsheet = client.open_by_key(spreadsheet_id)
    else:
        spreadsheet = client.open(title=title)

    sheet = spreadsheet.worksheet(sheet_name)
    return {
        "status": "success",
        "message": f"Read sheet '{sheet_name}' from spreadsheet '{spreadsheet.title}' successfully.",
        "table": sheet_to_markdown(sheet),
    }

@mcp_server.tool()
def insert_row(
    ctx: Context,
    sheet_name: str,
    insert_index: int,
    spreadsheet_id: Optional[str] = None,
    title: Optional[str] = None
):
    """
    Add a row after the specified index in a spreadsheet.
    If both spreadsheet_id and title are provided, spreadsheet_id will be used.
    If neither is provided, it will return an error.
    If sheet_name is not provided, it will return an error.

    Args:
        spreadsheet_id (str, optional): The ID of the spreadsheet. Defaults to None.
        title (str, optional): The title of the spreadsheet. Defaults to None.
        sheet_name (str): The name of the sheet to add the row to.
        insert_index: (int): The index at which to insert the row (1-based).
    """
    client: Client = ctx.request_context.lifespan_context
    if not spreadsheet_id and not title:
        raise ValueError("Either spreadsheet_id or title must be provided.")
    elif spreadsheet_id:
        spreadsheet = client.open_by_key(spreadsheet_id)
    else:
        spreadsheet = client.open(title=title)

    sheet = spreadsheet.worksheet(sheet_name)
    sheet.insert_row([], insert_index)
    return {
        "status": "success",
        "message": f"Inserted row at index {insert_index} in sheet '{sheet_name}' of spreadsheet '{spreadsheet.title}'.",
        "table": sheet_to_markdown(sheet)
    }

@mcp_server.tool()
def del_row(
    ctx: Context,
    sheet_name: str,
    row_index: int,
    spreadsheet_id: Optional[str] = None,
    title: Optional[str] = None
):
    """
    Delete a row from a spreadsheet.
    If both spreadsheet_id and title are provided, spreadsheet_id will be used.
    If neither is provided, it will return an error.
    If sheet_name is not provided, it will return an error.

    Args:
        spreadsheet_id (str, optional): The ID of the spreadsheet. Defaults to None.
        title (str, optional): The title of the spreadsheet. Defaults to None.
        sheet_name (str): The name of the sheet to delete the row from.
        row_index (int): The index of the row to delete (1-based).
    """
    client: Client = ctx.request_context.lifespan_context
    if not spreadsheet_id and not title:
        raise ValueError("Either spreadsheet_id or title must be provided.")
    elif spreadsheet_id:
        spreadsheet = client.open_by_key(spreadsheet_id)
    else:
        spreadsheet = client.open(title=title)

    sheet = spreadsheet.worksheet(sheet_name)
    sheet.delete_rows(row_index)
    return {
        "status": "success",
        "message": f"Deleted row at index {row_index} in sheet '{sheet_name}' of spreadsheet '{spreadsheet.title}'.",
        "table": sheet_to_markdown(sheet)
    }

@mcp_server.tool()
def del_col(
    ctx: Context,
    sheet_name: str,
    col_index: int,
    spreadsheet_id: Optional[str] = None,
    title: Optional[str] = None
):
    """
    Delete a column from a spreadsheet.
    If both spreadsheet_id and title are provided, spreadsheet_id will be used.
    If neither is provided, it will return an error.
    If sheet_name is not provided, it will return an error.

    Args:
        spreadsheet_id (str, optional): The ID of the spreadsheet. Defaults to None.
        title (str, optional): The title of the spreadsheet. Defaults to None.
        sheet_name (str): The name of the sheet to delete the column from.
        col_index (int): The index of the column to delete (1-based).
    """
    client: Client = ctx.request_context.lifespan_context
    if not spreadsheet_id and not title:
        raise ValueError("Either spreadsheet_id or title must be provided.")
    elif spreadsheet_id:
        spreadsheet = client.open_by_key(spreadsheet_id)
    else:
        spreadsheet = client.open(title=title)

    sheet = spreadsheet.worksheet(sheet_name)
    sheet.delete_columns(col_index)

    return {
        "status": "success",
        "message": f"Deleted column at index {col_index} in sheet '{sheet_name}' of spreadsheet '{spreadsheet.title}'.",
        "table": sheet_to_markdown(sheet)
    }

@mcp_server.tool()
def update_cell(
    ctx: Context,
    sheet_name: str,
    row_index: int,
    col_index: int,
    new_value: str,
    spreadsheet_id: Optional[str] = None,
    title: Optional[str] = None
):
    """
    Update a cell in a spreadsheet.
    If both spreadsheet_id and title are provided, spreadsheet_id will be used.
    If neither is provided, it will return an error.
    If sheet_name is not provided, it will return an error.

    Args:
        spreadsheet_id (str, optional): The ID of the spreadsheet. Defaults to None.
        title (str, optional): The title of the spreadsheet. Defaults to None.
        sheet_name (str): The name of the sheet to update the cell in.
        row_index (int): The row index of the cell to update (1-based).
        col_index (int): The column index of the cell to update (1-based).
        new_value (str): The new value for the cell.
    """
    client: Client = ctx.request_context.lifespan_context
    if not spreadsheet_id and not title:
        raise ValueError("Either spreadsheet_id or title must be provided.")
    elif spreadsheet_id:
        spreadsheet = client.open_by_key(spreadsheet_id)
    else:
        spreadsheet = client.open(title=title)

    sheet = spreadsheet.worksheet(sheet_name)
    sheet.update_cell(row_index, col_index, new_value)

    return {
        "status": "success",
        "message": f"Updated cell at ({row_index}, {col_index}) in sheet '{sheet_name}' of spreadsheet '{spreadsheet.title}' to '{new_value}'.",
        "table": sheet_to_markdown(sheet)
    }
