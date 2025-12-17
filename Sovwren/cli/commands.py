"""Command handler for CLI interface"""
import shlex
from typing import List, Optional
from .themes import theme

class CommandHandler:
    def __init__(self, cli_instance):
        self.cli = cli_instance

    async def handle_command(self, command_line: str):
        """Parse and handle CLI commands"""
        try:
            args = shlex.split(command_line)
            if not args:
                return

            command = args[0].lower()
            command_args = args[1:] if len(args) > 1 else []

            # Route commands
            if command == "help":
                self.cli.show_help()
                
            elif command == "models":
                await self.cli.list_models()

            elif command == "model":
                if command_args:
                    await self.cli.switch_model(command_args[0])
                else:
                    await self.cli.list_models()

            elif command == "switch":
                if command_args:
                    await self.cli.switch_model(command_args[0])
                else:
                    theme.print_error("Usage: /switch <model_name>")
                    
            elif command == "scrape":
                if command_args:
                    await self.cli.scrape_url(command_args[0])
                else:
                    theme.print_error("Usage: /scrape <url>")
                    
            elif command == "search":
                if command_args:
                    query = " ".join(command_args)
                    await self.cli.search_documents(query)
                else:
                    theme.print_error("Usage: /search <query>")
                    
            elif command == "stats":
                await self.cli.show_stats()
                
            elif command == "history":
                limit = 5
                if command_args and command_args[0].isdigit():
                    limit = int(command_args[0])
                self.cli.show_conversation_history(limit)
                
            elif command == "theme":
                if command_args:
                    self.cli.set_theme(command_args[0])
                else:
                    theme.print_error("Usage: /theme <theme_name>")
                    theme.print_info("Available themes: matrix, cyberpunk, minimal")
                    
            elif command == "clear":
                theme.clear_screen()
                theme.print_banner()
                
            elif command == "calendar":
                await self.cli.show_calendar()

            elif command == "month":
                # /month or /month 11 2025
                month = None
                year = None
                if len(command_args) >= 1:
                    month = int(command_args[0])
                if len(command_args) >= 2:
                    year = int(command_args[1])
                await self.cli.show_month_calendar(month, year)

            elif command == "event":
                if len(command_args) >= 2:
                    await self.cli.add_event(command_args)
                else:
                    theme.print_error("Usage: /event <date> <time> <title>")
                    theme.print_info("Example: /event 2025-11-10 14:30 Team meeting")

            elif command == "today":
                await self.cli.show_today_events()

            elif command == "complete":
                if command_args and command_args[0].isdigit():
                    await self.cli.complete_event(int(command_args[0]))
                else:
                    theme.print_error("Usage: /complete <event_id>")

            elif command == "mcp-servers":
                await self.cli.list_mcp_servers()

            elif command == "mcp-tools":
                server = command_args[0] if command_args else None
                await self.cli.list_mcp_tools(server)

            elif command == "mcp-call":
                if len(command_args) >= 3:
                    server = command_args[0]
                    tool = command_args[1]
                    args_json = " ".join(command_args[2:])
                    await self.cli.call_mcp_tool(server, tool, args_json)
                else:
                    theme.print_error("Usage: /mcp-call <server> <tool> <json_args>")
                    theme.print_info("Example: /mcp-call filesystem read_file '{\"path\": \"/tmp/test.txt\"}'")

            elif command == "report":
                self.cli.show_agent_report()

            elif command == "save-report":
                self.cli.save_agent_report()

            # RAG ingestion commands
            elif command == "ingest":
                if command_args:
                    path = " ".join(command_args)
                    await self.cli.ingest_path(path)
                else:
                    # Default: ingest full Sovwren corpus
                    await self.cli.ingest_corpus()

            elif command == "ingest-corpus":
                await self.cli.ingest_corpus()

            # ==================== Session Commands ====================
            elif command == "sessions":
                await self.cli.show_sessions()

            elif command == "resume":
                if command_args:
                    await self.cli.resume_session(command_args[0])
                else:
                    theme.print_error("Usage: /resume <session_number or session_id>")
                    theme.print_info("Use /sessions to see available sessions")

            elif command == "name":
                if command_args:
                    name = " ".join(command_args)
                    await self.cli.name_session(name)
                else:
                    theme.print_error("Usage: /name <session_name>")

            elif command == "new":
                await self.cli.start_new_session()

            elif command == "delete":
                if command_args:
                    await self.cli.delete_session(command_args[0])
                else:
                    theme.print_error("Usage: /delete <session_number or session_id>")

            elif command in ["exit", "quit", "bye"]:
                if theme.confirm("Are you sure you want to exit?"):
                    self.cli.running = False

            else:
                theme.print_error(f"Unknown command: /{command}")
                theme.print_info("Type '/help' for available commands")

        except Exception as e:
            theme.print_error(f"Command error: {e}")