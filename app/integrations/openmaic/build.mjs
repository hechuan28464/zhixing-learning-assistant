import {build} from 'esbuild';
import {mkdir,copyFile} from 'node:fs/promises';
await build({entryPoints:['integrations/openmaic/bridge.ts'],outfile:'integrations/openmaic/bridge.mjs',bundle:true,platform:'node',format:'esm',target:'node22',legalComments:'inline'});
await mkdir('integrations/openmaic/LICENSES',{recursive:true});
await copyFile('vendor/openmaic-v1.4.0/LICENSE','integrations/openmaic/LICENSES/OpenMAIC-MIT.txt');
await copyFile('node_modules/zod/LICENSE','integrations/openmaic/LICENSES/Zod-MIT.txt');
