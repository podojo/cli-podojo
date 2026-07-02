import typer

from .commands import (
    aiinterviews,
    auth,
    interviews,
    projects,
    showreel,
    synth,
    transcripts,
    usertests,
    videos,
)
from .version_check import check_for_update

app = typer.Typer(
    name="podojo",
    help="CLI for the Podojo user research platform",
    no_args_is_help=True,
)


@app.callback()
def root() -> None:
    check_for_update()


app.add_typer(auth.app, name="auth")
app.add_typer(projects.app, name="projects")
app.add_typer(interviews.app, name="interviews")
app.add_typer(usertests.app, name="usertests")
app.add_typer(aiinterviews.app, name="aiinterviews")
app.add_typer(synth.app, name="synth")
app.add_typer(transcripts.app, name="transcripts")
app.add_typer(videos.app, name="videos")
app.add_typer(showreel.app, name="showreel")

if __name__ == "__main__":
    app()
