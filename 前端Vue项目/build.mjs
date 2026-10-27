import { build } from 'esbuild';
import { copyFile, mkdir } from 'node:fs/promises';
const target = '../JavaWeb/src/main/resources/static';
await mkdir(target + '/assets', {recursive:true});
await build({entryPoints:['src/main.js'], bundle:true, minify:true, alias:{vue:'vue/dist/vue.esm.js'}, outfile:target+'/assets/app.js', loader:{'.woff':'file','.ttf':'file'}, assetNames:'[name]-[hash]'});
await copyFile('src/index.html',target+'/index.html');
