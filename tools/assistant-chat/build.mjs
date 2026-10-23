import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
const root=new URL('./node_modules/',import.meta.url),out=new URL('../../harvey/web/vendor/',import.meta.url);
await mkdir(out,{recursive:true});
const source=(await readFile(new URL('deep-chat/dist/deepChat.bundle.js',root),'utf8')).replace(/\/\/# sourceMappingURL=.*$/gm,'');
await writeFile(new URL('deep-chat-2.5.1.js',out),source);
const lock=JSON.parse(await readFile(new URL('./package-lock.json',import.meta.url),'utf8'));
let notices='Deep Chat 2.5.1 and dependency notices\nBundled locally; no CDN, direct model API, telemetry or browser storage configured.\n\n';
for(const [path,pkg] of Object.entries(lock.packages)){
 if(!path.startsWith('node_modules/'))continue;
 const dir=new URL('./'+path+'/',import.meta.url);
 notices+='\n'+path+' '+pkg.version+' ('+pkg.license+')\n';
 for(const name of await readdir(dir))if(/^(license|licence|copying|notice)(\.|$)/i.test(name))notices+=await readFile(new URL(name,dir),'utf8')+'\n';
}
await writeFile(new URL('deep-chat-LICENSE.txt',out),notices);
