// Runs the suite with explorer/display.json pinned to test/display.test.json,
// so no test depends on the zone or repos a checkout committed (the kit ships
// another zone, an adopter a third). Only tests that read the committed file
// on purpose (the build --check tests, the display-file validation) go through
// loadDisplay() / buildDatasets(), which read the file itself, not this seam.
import { register } from 'node:module';
register('./pin-display.mjs', import.meta.url);
await import('./suite.js');
