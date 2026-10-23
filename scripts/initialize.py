"""Initialize empty development state without changing existing state."""
import asyncio
from pathlib import Path

from harvey.signals import seed_signal_catalog
from harvey.state import StateManager


async def main():
    db = Path(__file__).resolve().parent.parent / "data" / "harvey.db"
    fresh = not db.exists()
    db.parent.mkdir(exist_ok=True)
    state = StateManager(str(db))
    await state.init_db()
    await seed_signal_catalog(state)
    if fresh:
        await state.set_setting("sending_paused", "Neutral development environment")
    print("Lokale Datenbank und Signalkatalog bereit.")


if __name__ == "__main__":
    asyncio.run(main())
