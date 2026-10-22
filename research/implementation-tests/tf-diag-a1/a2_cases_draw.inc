            case OP_DRAW: if (g_rc_skip) { ssbo_obs_draw_skipped(); imgdiag_draw_skipped(); break; } g_exec_next = p + h.size; imgdiag_draw(); ssbo_obs_draw(); draw(a, NULL); g_exec_next = NULL; break;   // Lookahead start point
            case OP_DRAW_IDX: if (g_rc_skip) { ssbo_obs_draw_skipped(); imgdiag_draw_skipped(); break; } g_exec_next = p + h.size; imgdiag_draw(); ssbo_obs_draw(); draw(NULL, a); g_exec_next = NULL; break;
            // Do not mark dirty if the state did not change (the game often re-sends the same program / state block / vertex format before each draw; the dirty flag only decides whether to re-fetch the pipeline / depth-stencil object, and equal values mean the same object)
            // One case of its own, NOT inside the label chain below: a label chain shares one body, so inserting a case in
            // the middle makes every earlier label fall into it and run that body with the wrong opcode.
