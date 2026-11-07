"""Run the production build with the toolchain options exported."""
import os
import subprocess

OPTIONS = {"log_format": "json", "jobs": "4"}
PREFIX = "ACME_"


def main():
    env = dict(os.environ)
    env.update({PREFIX + key.upper(): value for key, value in OPTIONS.items()})
    subprocess.run(["npm", "run", "build"], env=env, check=True)


if __name__ == "__main__":
    main()
