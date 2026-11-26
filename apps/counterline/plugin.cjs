'use strict';
// Thin Core hooks; business code lives under src/.
module.exports = { ...require('./src/model.cjs'), ...require('./src/operations.cjs'), ...require('./src/events.cjs') };
