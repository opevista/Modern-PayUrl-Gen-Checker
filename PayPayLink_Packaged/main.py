import typer
from paypay_link import generator, checker
from gui import PayPayApp, get_user_file_path

app = typer.Typer()

@app.command()
def generate(
    count: int = typer.Option(10, "--count", "-c", help="Number of links to generate."),
    delay: float = typer.Option(0, "--delay", "-d", help="Delay between generation in seconds."),
    output: str = typer.Option("paylink.txt", "--output", "-o", help="Output file name."),
):
    """
    Generate PayPay links.
    """
    generator.generate_links(count, delay, output)

@app.command()
def check(
    file: str = typer.Argument("paylink.txt", help="File name containing links to check."),
    delay: int = typer.Option(3000, "--delay", "-d", help="Delay between checks in milliseconds."),
    output: str = typer.Option("success_link.txt", "--output", "-o", help="Output file for successful links."),
):
    """
    Check PayPay links.
    """
    checker.check_links(file, delay, output)

@app.command()
def gui():
    """
    Launch the Textual GUI.
    """
    app = PayPayApp()
    app.run()

if __name__ == "__main__":
    app = PayPayApp()
    app.run()
