import {readFile,writeFile} from 'node:fs/promises';
const root=new URL('./node_modules/',import.meta.url);
const out=new URL('../../harvey/web/vendor/',import.meta.url);
for(const [src,dest] of [['dist/js/tom-select.complete.min.js','tom-select-2.6.2.js'],['dist/css/tom-select.css','tom-select-2.6.2.css']]){
 let content=await readFile(new URL('tom-select/'+src,root),'utf8');
 content=content.replace(/\/\/# sourceMappingURL=.*$/gm,'').replace(/\/\*# sourceMappingURL=.*?\*\//gs,'');
 await writeFile(new URL(dest,out),content);
}
let notices='Tom Select 2.6.2 and bundled dependencies (Apache-2.0)\n\n';
notices+=await readFile(new URL('tom-select/LICENSE',root),'utf8');
for(const name of ['@orchidjs/sifter','@orchidjs/unicode-variants']){
 const pkg=JSON.parse(await readFile(new URL(name+'/package.json',root),'utf8'));
 const readme=await readFile(new URL(name+'/README.md',root),'utf8');
 notices+='\n\n'+name+' '+pkg.version+'\n'+readme.slice(readme.lastIndexOf('## License'))+'\n';
}
await writeFile(new URL('tom-select-LICENSE.txt',out),notices);
