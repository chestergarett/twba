"""
Authentication module for TWBA Dashboard.
Handles login, logout, and authentication state management.
"""
import dash
from dash import dcc, html, Input, Output, callback, State
import dash_bootstrap_components as dbc


def create_login_page(error_message=""):
    """Create the login page UI."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1("TWBA Analytics Dashboard", className="text-center mb-4"),
                    html.Hr(),
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Login", className="text-center mb-4"),
                            dbc.Input(
                                id="login-username",
                                type="text",
                                placeholder="Username",
                                className="mb-3"
                            ),
                            dbc.Input(
                                id="login-password",
                                type="password",
                                placeholder="Password",
                                className="mb-3"
                            ),
                            dbc.Button("Login", id="login-button", color="primary", className="w-100 mb-2"),
                            html.Div(id="login-message", children=[
                                dbc.Alert(error_message, color="danger", className="mb-0") if error_message else ""
                            ], className="text-center mt-3")
                        ])
                    ], className="shadow")
                ], style={"maxWidth": "400px", "margin": "0 auto", "paddingTop": "100px"})
                ])
            ])
        ], fluid=True)


def register_auth_callbacks(app, create_dashboard_layout, auth_username, auth_password):
    """
    Register authentication callbacks with the Dash app.
    
    Args:
        app: Dash app instance
        create_dashboard_layout: Function to create dashboard layout
        auth_username: Username for authentication
        auth_password: Password for authentication
    """
    # Store for authentication state - using session storage to persist across page refreshes
    auth_store = dcc.Store(id="auth-store", data={"authenticated": False}, storage_type="session")
    
    @callback(
        Output("page-content", "children", allow_duplicate=True),
        Input("auth-store", "data"),
        prevent_initial_call='initial_duplicate',
    )
    def check_auth_on_load(auth_data):
        """Check authentication state on page load."""
        try:
            if auth_data and isinstance(auth_data, dict) and auth_data.get("authenticated"):
                return create_dashboard_layout()
            else:
                return create_login_page()
        except Exception as e:
            # If there's an error, show login page
            print(f"Error in check_auth_on_load: {e}")
            return create_login_page()

    # Callback to handle login
    @app.callback(
        Output("page-content", "children", allow_duplicate=True),
        Output("auth-store", "data", allow_duplicate=True),
        Input("login-button", "n_clicks"),
        State("auth-store", "data"),
        State("login-username", "value"),
        State("login-password", "value"),
        prevent_initial_call=True,
    )
    def handle_login(n_clicks, auth_data, username, password):
        """Handle login button click."""
        if n_clicks:
            # Validate credentials
            if username == auth_username and password == auth_password:
                try:
                    return create_dashboard_layout(), {"authenticated": True}
                except Exception as e:
                    print(f"Error in handle_login: {e}")
                    return create_login_page("Error loading dashboard. Please try again."), {"authenticated": False}
            else:
                # Show error message but stay on login page
                error_message = "Invalid username or password"
                return create_login_page(error_message), {"authenticated": False}
        
        return dash.no_update, dash.no_update

    # Callback to handle logout
    @app.callback(
        Output("page-content", "children", allow_duplicate=True),
        Output("auth-store", "data", allow_duplicate=True),
        Input("logout-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def handle_logout(n_clicks):
        """Handle logout button click."""
        if n_clicks:
            return create_login_page(), {"authenticated": False}
        return dash.no_update, dash.no_update
    
    return auth_store

