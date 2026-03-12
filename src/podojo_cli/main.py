import typer

from .commands import auth, projects, showreel, transcripts, videos

app = typer.Typer(
    name="podojo",
    help="CLI for the Podojo user research platform",
    no_args_is_help=True,
)

app.add_typer(auth.app, name="auth")
app.add_typer(projects.app, name="projects")
app.add_typer(transcripts.app, name="transcripts")
app.add_typer(videos.app, name="videos")
app.add_typer(showreel.app, name="showreel")

if __name__ == "__main__":
    app()
