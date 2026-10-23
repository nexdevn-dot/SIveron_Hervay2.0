import fs from 'node:fs';
import path from 'node:path';
const roots=fs.readdirSync('node_modules').filter(n=>n!=='.bin').flatMap(n=>n.startsWith('@')?fs.readdirSync(path.join('node_modules',n)).map(x=>path.join('node_modules',n,x)):[path.join('node_modules',n)]);
const sections=[];
for(const root of roots){
 const file=path.join(root,'package.json');if(!fs.existsSync(file))continue;
 const pkg=JSON.parse(fs.readFileSync(file,'utf8'));
 const licenses=fs.readdirSync(root).filter(n=>/^licen[sc]e(?:\.|$)/i.test(n));
 sections.push(`${pkg.name} ${pkg.version} (${pkg.license||'see package'})\n${licenses.map(n=>fs.readFileSync(path.join(root,n),'utf8')).join('\n')}`);
}
fs.writeFileSync('../../harvey/web/vendor/campaign-editor-LICENSES.txt',sections.join('\n\n========================================\n\n'));
