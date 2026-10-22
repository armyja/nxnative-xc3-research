case OP_END: g_exec_cur = NULL;
                if (g_hoist_n && !g_ret_n && !g_nrest) {
                    if (g_fz.active) fz_unskip();
                    if (g_hoist_n) { MLOG("[RED] pure-clear pass hoisting: %d hoisted operations were not reached by the end of the submission; cleared (should not happen)", g_hoist_n); g_hoist_n = 0; }
                }
                tf_diag_leave();
                return;   // An end-of-pass triggered outside a list (present / CPU readback etc.) must not scan expired command memory: a null start point means store everything
            case OP_BEGIN: break;
            