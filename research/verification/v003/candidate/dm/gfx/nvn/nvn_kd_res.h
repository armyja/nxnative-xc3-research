// Read-only, default-off GS resource observer. Pure formatting/identity/registry helpers; the caller copies
// scalars from its own state. No allocation, no guest memory read, no MTL lookup, no object creation.
#ifndef NVN_KD_RES_H
#define NVN_KD_RES_H
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>

#define KDR_MAX_KEYS 6
#define KDR_MAX_SLOTS 9
#define KDR_REC_CAP 8192

typedef enum { KDR_HIT=0, KDR_TARGET_NOT_OBTAINED, KDR_NO_GEOMETRY_SOURCE, KDR_IDENTITY_UNAVAILABLE,
               KDR_GS_KEY_MISMATCH, KDR_INVALID_CONFIG, KDR_DIAG_ERROR } kdr_result;

typedef struct { int present, nstage, have[KDR_MAX_KEYS]; uint8_t key[KDR_MAX_KEYS][8]; int query_calls; } kdr_gs_keys;
typedef struct { uint64_t mask[2]; uint32_t n; uint32_t slot[KDR_MAX_SLOTS]; uint64_t handle[KDR_MAX_SLOTS]; uint32_t omitted; } kdr_slots;

typedef struct {
    kdr_result result;
    char vs[24], ps[24], ps_style[16];     // actual keys and bare/_b/_bf/other classification
    kdr_gs_keys gs;
    uint64_t frame, pass;
    int drawkind;                            // 0 direct, 1 indexed
    int prim, count, instances, base_instance, indirect;
    int ubo_avail, tex_avail, samp_avail;
    uint16_t ubo_mask;
    uint64_t ubo0_addr, ubo0_size;
    kdr_slots tex, samp;
    int tex_candidate, tex_hint_avail;
    uint64_t tex_raw, tex_hint_ser;
    uint32_t tex_tid;
    int tex_registry_checked, tex_registered, tex_desc_avail;
    int32_t tex_target, tex_format;
    uint32_t tex_w, tex_h, tex_d, tex_samples;
    uint64_t tex_reg_serial;
    int samp_candidate, samp_registry_checked, samp_registered, samp_desc_avail;
    uint64_t samp_raw, samp_sid64, samp_reg_serial;
    uint32_t samp_minf, samp_magf, samp_ws, samp_wt, samp_wr, samp_cmp_mode, samp_cmp_func;
    uint32_t samp_lod_min_bits, samp_lod_max_bits, samp_lod_bias_bits, samp_aniso_bits;
    uint32_t samp_border_bits[4];
    int tf_known;                            // must remain 0: no host TF state
} kdr_record;

typedef struct { int ok; int32_t target, format; uint32_t w,h,d,samples; uint64_t serial; } kdr_tex_ent;
typedef struct { int ok; uint32_t minf,magf,ws,wt,wr,cmp_mode,cmp_func; uint32_t lod_min_bits,lod_max_bits,lod_bias_bits,aniso_bits; uint32_t border_bits[4]; } kdr_samp_ent;

static inline int kdr_gs_identity(kdr_gs_keys *g, const uint8_t target[8], kdr_result *why) {
    if (!g->present) { *why=KDR_NO_GEOMETRY_SOURCE; return 0; }
    if (g->nstage <= 0 || g->nstage > KDR_MAX_KEYS) { *why=KDR_IDENTITY_UNAVAILABLE; return 0; }
    int hit=0, unknown=0;
    for (int i=0;i<g->nstage;i++) {
        if (!g->have[i]) { unknown=1; continue; }
        if (memcmp(g->key[i], target, 8)==0) hit=1;
    }
    if (hit) { *why=KDR_HIT; return 1; }
    *why = unknown ? KDR_IDENTITY_UNAVAILABLE : KDR_GS_KEY_MISMATCH;
    return 0;
}
static inline int kdr_tex_entry_ok(uint32_t tid, int ntreg, const kdr_tex_ent *e) {
    return e && tid > 0 && ntreg > 0 && tid < (uint32_t)ntreg && e->ok;
}
static inline int kdr_samp_entry_ok(uint64_t sid64, int nsreg, const kdr_samp_ent *e) {
    return e && nsreg > 0 && sid64 < (uint64_t)nsreg && e->ok;
}
static inline int kdr_tex_lookup_ok(uint64_t raw, uint32_t tid, int ntreg, const kdr_tex_ent *arr, kdr_tex_ent *out) {
    if (!arr || tid == 0 || tid >= (uint32_t)ntreg || ntreg <= 0) return 0;
    const kdr_tex_ent *e=&arr[tid]; if (!e->ok) return 0; if(out)*out=*e; return 1;
}
static inline int kdr_samp_lookup_ok(uint64_t raw, uint64_t sid64, int nsreg, const kdr_samp_ent *arr, kdr_samp_ent *out) {
    if (!arr || sid64 >= (uint64_t)nsreg || nsreg <= 0) return 0;
    const kdr_samp_ent *e=&arr[sid64]; if (!e->ok) return 0; if(out)*out=*e; return 1;
}

static inline int kdr_hexbyte(const char *s, uint8_t *v) {
    int a=0,b=0;
    for(int i=0;i<2;i++){char c=s[i]; int d=(c>='0'&&c<='9')?c-'0':(c>='a'&&c<='f')?c-'a'+10:-1; if(d<0)return 0; if(!i)a=d;else b=d;}
    *v=(uint8_t)((a<<4)|b); return 1;
}
static inline int kdr_parse_cfg(const char *e, uint8_t gs[8], uint8_t ps[8]) {
    if (!e || !*e) return -1;
    if (strlen(e)!=33 || e[16]!=':') return 0;
    for(int i=0;i<8;i++){ if(!kdr_hexbyte(e+2*i,&gs[i]) || !kdr_hexbyte(e+17+2*i,&ps[i])) return 0; }
    return 1;
}

static inline int kdr_ps_style(const char *key, char *sty, size_t cap) {
    if (!key) { snprintf(sty,cap,"invalid"); return -1; }
    size_t n = strlen(key);
    if (n < 16) { snprintf(sty,cap,"invalid"); return -1; }
    for (size_t i=0;i<16 && i<n;i++) if (!((key[i]>='0'&&key[i]<='9')||(key[i]>='a'&&key[i]<='f'))) { snprintf(sty,cap,"invalid"); return -1; }
    if (n == 16) { snprintf(sty,cap,"bare"); return 0; }
    if (n == 17) { snprintf(sty,cap,"invalid"); return -1; }
    if (n == 18 && key[16]=='_' && key[17]=='b') { snprintf(sty,cap,"_b"); return 1; }
    if (n == 19 && key[16]=='_' && key[17]=='b' && key[18]=='f') { snprintf(sty,cap,"_bf"); return 2; }
    snprintf(sty,cap,"other"); return 3;
}
static inline int kdr_append(char *b, size_t cap, size_t *at, const char *fmt, ...) {
    if (*at >= cap) return 0;
    va_list ap; va_start(ap,fmt); int n=vsnprintf(b+*at,cap-*at,fmt,ap); va_end(ap);
    if (n < 0 || (size_t)n >= cap-*at) return 0;
    *at += (size_t)n; return 1;
}
static inline int kdr_format(char *b, size_t cap, const kdr_record *r) {
    if (!b || !cap || !r) return 0;
    size_t at=0;
    if (!kdr_append(b,cap,&at,"[gs-res] result=%s vs=%s ps=%s ps_style=%s", r->result==KDR_HIT?"hit":r->result==KDR_TARGET_NOT_OBTAINED?"target-not-obtained":r->result==KDR_NO_GEOMETRY_SOURCE?"no-geometry-source":r->result==KDR_IDENTITY_UNAVAILABLE?"identity-unavailable":r->result==KDR_GS_KEY_MISMATCH?"gs-key-mismatch":"diagnostic-error", r->vs, r->ps, r->ps_style)) return 0;
    if (!kdr_append(b,cap,&at," frame=%llu pass_counter=%llu final_pass_association=none drawkind=%s prim=%d",(unsigned long long)r->frame,(unsigned long long)r->pass,r->drawkind?"indexed":"direct",r->prim)) return 0;
    if (r->indirect) { if(!kdr_append(b,cap,&at," count=unavailable instances=unavailable base_instance=unavailable indirect=1")) return 0; }
    else { if(!kdr_append(b,cap,&at," count=%d instances=%d base_instance=%d indirect=0",r->count,r->instances,r->base_instance)) return 0; }
    if (!kdr_append(b,cap,&at," gs_present=%d nstage=%d gs_query_calls=%d keys=",r->gs.present,r->gs.nstage,r->gs.query_calls)) return 0;
    for(int i=0;i<r->gs.nstage && i<KDR_MAX_KEYS;i++) { if(i && !kdr_append(b,cap,&at,",")) return 0; if(r->gs.have[i]) { if(!kdr_append(b,cap,&at,"%02x%02x%02x%02x%02x%02x%02x%02x",r->gs.key[i][0],r->gs.key[i][1],r->gs.key[i][2],r->gs.key[i][3],r->gs.key[i][4],r->gs.key[i][5],r->gs.key[i][6],r->gs.key[i][7])) return 0; } else if(!kdr_append(b,cap,&at,"unknown")) return 0; }
    if (!kdr_append(b,cap,&at," ubo_avail=%d ubo_mask=%04x ubo0=%s addr=%#llx size=%llu contents=unavailable",r->ubo_avail,r->ubo_mask,r->ubo_avail?"present":"unavailable",(unsigned long long)r->ubo0_addr,(unsigned long long)r->ubo0_size)) return 0;
    if (!kdr_append(b,cap,&at," tex_avail=%d tex_mask=%016llx%016llx tex_n=%u tex_omitted=%u",r->tex_avail,(unsigned long long)r->tex.mask[1],(unsigned long long)r->tex.mask[0],r->tex.n,r->tex.omitted)) return 0;
    for(uint32_t i=0;i<r->tex.n && i<KDR_MAX_SLOTS;i++) if(!kdr_append(b,cap,&at," tex%d=%#llx",r->tex.slot[i],(unsigned long long)r->tex.handle[i])) return 0;
    if (!kdr_append(b,cap,&at," samp_avail=%d samp_mask=%016llx%016llx samp_n=%u samp_omitted=%u",r->samp_avail,(unsigned long long)r->samp.mask[1],(unsigned long long)r->samp.mask[0],r->samp.n,r->samp.omitted)) return 0;
    for(uint32_t i=0;i<r->samp.n && i<KDR_MAX_SLOTS;i++) if(!kdr_append(b,cap,&at," samp%d=%#llx",r->samp.slot[i],(unsigned long long)r->samp.handle[i])) return 0;
    if(!kdr_append(b,cap,&at," tex_candidate=%d raw=%#llx hint=%s hint_ser=%#llx registry_checked=%d registered=%d desc=%s target=%d format=%d %ux%ux%u samples=%u reg_serial=%llu",r->tex_candidate,(unsigned long long)r->tex_raw,r->tex_hint_avail?"present":"unavailable",(unsigned long long)r->tex_hint_ser,r->tex_registry_checked,r->tex_registered,r->tex_desc_avail?"present":"unavailable",r->tex_target,r->tex_format,r->tex_w,r->tex_h,r->tex_d,r->tex_samples,(unsigned long long)r->tex_reg_serial)) return 0;
    if(!kdr_append(b,cap,&at," samp_candidate=%d raw=%#llx sid_u64=%llu registry_checked=%d registered=%d desc=%s minf=%u magf=%u wrap=%u,%u,%u cmp=%u/%u lod_bits=%08x,%08x,%08x aniso_bits=%08x border_bits=%08x,%08x,%08x,%08x reg_serial=unavailable",r->samp_candidate,(unsigned long long)r->samp_raw,(unsigned long long)r->samp_sid64,r->samp_registry_checked,r->samp_registered,r->samp_desc_avail?"present":"unavailable",r->samp_minf,r->samp_magf,r->samp_ws,r->samp_wt,r->samp_wr,r->samp_cmp_mode,r->samp_cmp_func,r->samp_lod_min_bits,r->samp_lod_max_bits,r->samp_lod_bias_bits,r->samp_aniso_bits,r->samp_border_bits[0],r->samp_border_bits[1],r->samp_border_bits[2],r->samp_border_bits[3])) return 0;
    if(!kdr_append(b,cap,&at," tf=%s bind_source=current_S_state",r->tf_known?"known":"unknown")) return 0;
    return 1;
}
#endif
