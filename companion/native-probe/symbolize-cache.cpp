// SPDX-License-Identifier: AGPL-3.0-or-later
// Owned read-only adapter for InfernoFSPatcher's separately obtained AGPL parser.
// Header implementation: Visual Ehrmanntraut, InfernoFSPatcher (see README).
#include "analyser.hpp"
#include <iostream>
#include <map>
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    CacheAnalyser analyser(argv[1]);
    auto images=analyser.main_cache().second.images;
    std::sort(images.begin(),images.end(),[](const auto&a,const auto&b){return a.base<b.base;});
    std::map<std::string,std::map<uint64_t,std::string>> symbols;
    uint64_t address;
    while(std::cin>>std::hex>>address) {
        auto pos=std::upper_bound(images.begin(),images.end(),address,[](auto v,const auto&i){return v<i.base;});
        if(pos==images.begin()){std::cout<<std::hex<<address<<"\tUNMAPPED\n";continue;}--pos;
        if(!symbols.count(pos->path)) {
            auto image=analyser.find_image(ImageMatch(pos->path));
            auto &table=symbols[pos->path];for(const auto &symbol:image.symbols)table.emplace(symbol.second,symbol.first);
        }
        const auto &table=symbols[pos->path];auto sym=table.upper_bound(address);
        std::cout<<std::hex<<address<<'\t'<<pos->path<<'\t';
        if(sym!=table.begin()){--sym;std::cout<<sym->second<<" +0x"<<(address-sym->first);}else std::cout<<"NO_SYMBOL";
        std::cout<<'\n';
    }
}
