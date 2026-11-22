# Upstream source

OpenMAIC v1.4.0, commit `795420c12f7846577468fc7831437db6eb957e14`.

Source: https://github.com/THU-MAIC/OpenMAIC/tree/v1.4.0/lib/pbl/v3/domain

The `domain` files are copied without functional changes under the included MIT license. The application calls their real schema, state transitions and stage gates via a fixed Node JSON bridge. Learner code is not executed by this bridge.

This integration adapts persistence, teaching messages and execution to 知行伴学; it does not deploy the complete upstream Next.js/PostgreSQL/E2B runtime. It must not be described as full upstream-hosted PBL v3 acceptance. Local deployment uses a separate constrained Docker execution service and persistent files instead of cloud sandbox accounts.

Zod 4.6.7 and esbuild 0.28.2 are pinned in this host after registry audit; upstream's older package versions were not copied. Compatibility is verified through the contract tests.
