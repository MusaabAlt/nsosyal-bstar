# Raw output dump — 2026-08-23

Generated from disk. Every block below is either the verbatim contents of a
file or the captured stdout of the command shown. Nothing was transcribed by
hand.

---

## 1. `grep -rn "conf" --include=*.py`

Command as run (the bare form times out at 120 s on this repo):

```
grep -rn "conf" --include=*.py --exclude-dir=.venv --exclude-dir=venv --exclude-dir=__pycache__ .
```

Exit code 0. 334 matching lines.

```
./config.py:1:"""Central path + constant configuration for NSosyal B*.
./config.py:18:Set these BEFORE importing config:
./config.py:21:    import config
./conftest.py:1:"""Put the repo root on sys.path so tests can `import config` / `from src import ...`
./day1_gate_en.py:21:Inputs  : config.COLTEKIN_TRAIN, config.LEXICON_PATH (override with flags)
./day1_gate_en.py:40:    sys.stdout.reconfigure(encoding="utf-8")
./day1_gate_en.py:46:import config
./day1_gate_en.py:52:    ap.add_argument("--train", default=None, help="OffensEval-TR training TSV (default: config)")
./day1_gate_en.py:53:    ap.add_argument("--lexicon", default=None, help="Frozen lexicon file (default: config)")
./day1_gate_en.py:58:    train_path = Path(args.train or config.COLTEKIN_TRAIN)
./day1_gate_en.py:59:    lex_path = Path(args.lexicon or config.LEXICON_PATH)
./day1_gate_en.py:60:    out_path = Path(args.out or config.RESULTS_DIR / "day1_report.json")
./day1_gate_en.py:144:    rng = random.Random(config.SEED)  # fixed seed -> reproducible sample
./day1_gate_en.py:158:        "seed": config.SEED,
./demo/app.py:78:    # work with and its confidence should not be read as meaningful.
./demo/app.py:81:                     "signal here and its confidence is not meaningful")
./demo/app.py:132:           "systems": {"keyword": {"decision": kw, "confidence": None,
./demo/app.py:137:        out["systems"][name] = {"decision": d, "confidence": p,
./demo/app.py:142:    p = out["systems"]["raw"]["confidence"]
./demo/app.py:143:    conf = max(p, 1.0 - p)
./demo/app.py:144:    auto = conf >= op["threshold"]
./demo/app.py:146:        "confidence": conf,
./demo/app.py:151:        "margin": conf - op["threshold"],
./demo/app.py:242:            conf = f"{s['confidence']:.4f}" if s["confidence"] is not None else "—"
./demo/app.py:245:                     f"<td>{conf}</td>"
./demo/app.py:262:  decision confidence max(p, 1-p) = <code>{sel['confidence']:.4f}</code>,
./demo/app.py:306:Review layer: raw BERTurk, confidence threshold <code>{op['threshold']:.4f}</code>,
./demo/app.py:379:        m = AutoModelForSequenceClassification.from_config(cfg)
./demo/app.py:420:                      f"raw={s['raw']['decision']}({s['raw']['confidence']:.3f}) "
./demo/build_assets.py:5:to be on local disk first: the tokenizer vocabulary and the model config come
./demo/build_assets.py:31:import config
./demo/build_assets.py:57:    # --- tokenizer + config: THE network step -----------------------------
./demo/build_assets.py:58:    print(f"fetching tokenizer + config for {MODEL_NAME} (this needs network) ...")
./demo/build_assets.py:66:    cfg.save_pretrained(out / "tokenizer")   # config lives beside the vocab
./demo/build_assets.py:78:    shutil.copy2(config.LEXICON_PATH, out / "lexicon" / "karaliste.txt")
./demo/build_assets.py:81:    calp = Path(args.calibration or config.RESULTS_DIR / "04_calibration" / "calibration.json")
./handoff_bundle/demo/app.py:78:    # work with and its confidence should not be read as meaningful.
./handoff_bundle/demo/app.py:81:                     "signal here and its confidence is not meaningful")
./handoff_bundle/demo/app.py:132:           "systems": {"keyword": {"decision": kw, "confidence": None,
./handoff_bundle/demo/app.py:137:        out["systems"][name] = {"decision": d, "confidence": p,
./handoff_bundle/demo/app.py:142:    p = out["systems"]["raw"]["confidence"]
./handoff_bundle/demo/app.py:143:    conf = max(p, 1.0 - p)
./handoff_bundle/demo/app.py:144:    auto = conf >= op["threshold"]
./handoff_bundle/demo/app.py:146:        "confidence": conf,
./handoff_bundle/demo/app.py:151:        "margin": conf - op["threshold"],
./handoff_bundle/demo/app.py:242:            conf = f"{s['confidence']:.4f}" if s["confidence"] is not None else "—"
./handoff_bundle/demo/app.py:245:                     f"<td>{conf}</td>"
./handoff_bundle/demo/app.py:262:  decision confidence max(p, 1-p) = <code>{sel['confidence']:.4f}</code>,
./handoff_bundle/demo/app.py:306:Review layer: raw BERTurk, confidence threshold <code>{op['threshold']:.4f}</code>,
./handoff_bundle/demo/app.py:379:        m = AutoModelForSequenceClassification.from_config(cfg)
./handoff_bundle/demo/app.py:420:                      f"raw={s['raw']['decision']}({s['raw']['confidence']:.3f}) "
./phase01_baseline.py:30:Inputs  : config.COLTEKIN_TRAIN, config.LEXICON_PATH
./phase01_baseline.py:32:          classification_report.txt, dev_predictions.csv, run_config.json,
./phase01_baseline.py:50:    sys.stdout.reconfigure(encoding="utf-8")
./phase01_baseline.py:56:import config
./phase01_baseline.py:112:    rerun = config.RESULTS_DIR / "day1_report_rerun.json"
./phase01_baseline.py:241:                    "run_config.json", "results_log_row.md")
./phase01_baseline.py:272:    # reads it for the failure analysis and phase 4 reads its confidence column
./phase01_baseline.py:284:                         "(calibration confidences) both read it.")
./phase01_baseline.py:323:    canonical = Path(config.RESULTS_DIR / RUN_ID).resolve()
./phase01_baseline.py:354:        c = s["confusion"]
./phase01_baseline.py:397:        w.writerow(["row_id", "text", "gold", "pred", "confidence", "slice"])
./phase01_baseline.py:399:            # confidence = softmax P(OFF); the failure analysis and the
./phase01_baseline.py:417:            "confusion": s["confusion"],  # {tn, fp, fn, tp} -- gold OFF = tp+fn
./phase01_baseline.py:421:                "(base rates 57.8% vs 13.6%); recompute from `confusion` if ever needed "
./phase01_baseline.py:434:            "confusion": kw["confusion"],
./phase01_baseline.py:445:                "confusion": overall["confusion"],
./phase01_baseline.py:467:    run_config = {
./phase01_baseline.py:472:        "env": config.ENV,
./phase01_baseline.py:473:        "paths": {"root": str(config.ROOT), "data": str(config.DATA_DIR),
./phase01_baseline.py:491:        run_config = {"MOCK_RUN": mock_note, **run_config}
./phase01_baseline.py:492:    with open(out_dir / "run_config.json", "w", encoding="utf-8") as f:
./phase01_baseline.py:493:        json.dump(run_config, f, ensure_ascii=False, indent=2)
./phase01_baseline.py:519:                 "run_config.json", "results_log_row.md"):
./phase01_baseline.py:533:    ap.add_argument("--model", default=config.MODEL_BASELINE)
./phase01_baseline.py:537:    ap.add_argument("--max_len", type=int, default=config.MAX_LEN)
./phase01_baseline.py:538:    ap.add_argument("--seed", type=int, default=config.SEED)
./phase01_baseline.py:562:    train_path = Path(config.COLTEKIN_TRAIN)
./phase01_baseline.py:563:    lex_path = Path(config.LEXICON_PATH)
./phase01_baseline.py:582:    split_path = config.SPLITS_DIR / f"split_seed{args.seed}.json"
./phase01_baseline.py:584:        all_rows, split_path, train_sha, seed=args.seed, dev_fraction=config.DEV_FRACTION
./phase01_baseline.py:632:    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
./phase01_baseline.py:633:    ckpt_dir = Path(args.ckpt_dir or config.CKPT_DIR / RUN_ID)
./phase01_baseline.py:636:    print(f"env={config.ENV}  root={config.ROOT}")
./phase01_baseline.py:637:    print(f"data={config.DATA_DIR}\nout={out_dir}\nckpt={ckpt_dir}\n")
./phase03_compare.py:26:    sys.stdout.reconfigure(encoding="utf-8")
./phase03_compare.py:32:import config
./phase03_compare.py:51:    ap.add_argument("--seed", type=int, default=config.SEED)
./phase03_compare.py:55:    runs_dir = Path(args.runs_dir or config.RESULTS_DIR / "03_defense")
./phase03_compare.py:80:                           with_ci=False)["confusion"]
./phase03_compare.py:100:            "lexicon_hit_fp_rate": fpr, "lexicon_hit_confusion": hc,
./phase03_make_augmentation.py:27:    sys.stdout.reconfigure(encoding="utf-8")
./phase03_make_augmentation.py:33:import config
./phase03_make_augmentation.py:42:    ap.add_argument("--seed", type=int, default=config.SEED)
./phase03_make_augmentation.py:48:    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
./phase03_make_augmentation.py:52:    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
./phase03_make_augmentation.py:53:    split_path = config.SPLITS_DIR / f"split_seed{args.seed}.json"
./phase03_make_augmentation.py:55:        all_rows, split_path, train_sha, seed=args.seed, dev_fraction=config.DEV_FRACTION)
./phase03_train_defense.py:35:    sys.stdout.reconfigure(encoding="utf-8")
./phase03_train_defense.py:41:import config
./phase03_train_defense.py:110:    hit = by_slice["lexicon_hit"]["confusion"]
./phase03_train_defense.py:124:        "off_precision": overall["off_precision"], "confusion": overall["confusion"],
./phase03_train_defense.py:130:        "lexicon_hit_confusion": hit,
./phase03_train_defense.py:131:        "lexicon_free_confusion": by_slice["lexicon_free"]["confusion"],
./phase03_train_defense.py:144:    ap.add_argument("--model", default=config.MODEL_BASELINE)
./phase03_train_defense.py:148:    ap.add_argument("--max_len", type=int, default=config.MAX_LEN)
./phase03_train_defense.py:149:    ap.add_argument("--seed", type=int, default=config.SEED)
./phase03_train_defense.py:162:    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID / f"run_{args.variant}")
./phase03_train_defense.py:163:    ckpt_dir = Path(args.ckpt_dir or config.CKPT_DIR / RUN_ID / args.variant)
./phase03_train_defense.py:169:    print(f"env={config.ENV}  out={out_dir}\n")
./phase03_train_defense.py:172:    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
./phase03_train_defense.py:173:    split_path = config.SPLITS_DIR / f"split_seed{args.seed}.json"
./phase03_train_defense.py:175:        all_rows, split_path, train_sha, seed=args.seed, dev_fraction=config.DEV_FRACTION)
./phase03_train_defense.py:232:          f"({res['lexicon_hit_confusion']['fp']}/{res['lexicon_hit_confusion']['fp'] + res['lexicon_hit_confusion']['tn']})")
./phase03_train_defense.py:258:            "off_precision": h_score["off_precision"], "confusion": h_score["confusion"],
./phase03_train_defense.py:270:        w.writerow(["row_id", "text", "gold", "pred", "confidence", "slice"])
./phase03_train_errors.py:31:Inputs  : config.COLTEKIN_TRAIN, config.LEXICON_PATH, the frozen split file
./phase03_train_errors.py:50:    sys.stdout.reconfigure(encoding="utf-8")
./phase03_train_errors.py:56:import config
./phase03_train_errors.py:68:    ap.add_argument("--model", default=config.MODEL_BASELINE)
./phase03_train_errors.py:72:    ap.add_argument("--max_len", type=int, default=config.MAX_LEN)
./phase03_train_errors.py:73:    ap.add_argument("--seed", type=int, default=config.SEED)
./phase03_train_errors.py:87:    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
./phase03_train_errors.py:89:    ckpt_dir = Path(args.ckpt_dir or config.CKPT_DIR / RUN_ID)
./phase03_train_errors.py:92:    print(f"env={config.ENV}  out={out_dir}\n")
./phase03_train_errors.py:95:    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
./phase03_train_errors.py:96:    split_path = config.SPLITS_DIR / f"split_seed{args.seed}.json"
./phase03_train_errors.py:98:        all_rows, split_path, train_sha, seed=args.seed, dev_fraction=config.DEV_FRACTION
./phase03_train_errors.py:144:            w.writerow(["row_id", "text", "gold", "pred", "confidence", "fold"])
./phase03_train_errors.py:161:        w = csv.DictWriter(fh, fieldnames=["row_id", "text", "gold", "pred", "confidence", "fold"])
./phase03_train_errors.py:194:            "confusion": overall["confusion"],
./phase04_calibration.py:32:    sys.stdout.reconfigure(encoding="utf-8")
./phase04_calibration.py:38:import config
./phase04_calibration.py:76:        "p_off": [float(r["confidence"]) for r in rows],
./phase04_calibration.py:86:        sys.exit(f"ABORT: {path} has {mismatch} rows where pred != argmax(confidence). "
./phase04_calibration.py:138:    rep["direction"] = ("overconfident" if gap < 0 else
./phase04_calibration.py:139:                        "underconfident" if gap > 0 else "neither")
./phase04_calibration.py:213:          f"(signed gap accuracy-confidence = {rep['ece']['before']['15']['signed_gap']:+.4f})")
./phase04_calibration.py:224:    print(f"  {'bin':<14}{'n':>6}{'acc':>9}{'conf':>9}{'gap':>9}   |"
./phase04_calibration.py:225:          f"{'n':>6}{'acc':>9}{'conf':>9}{'gap':>9}")
./phase04_calibration.py:234:                    f"{b['mean_confidence']:>9.4f}{b['gap']:>+9.4f}")
./phase04_calibration.py:280:    d = config.RESULTS_DIR / "03_defense"
./phase04_calibration.py:287:    ap.add_argument("--seed", type=int, default=config.SEED)
./phase04_calibration.py:291:    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
./phase05_final_test.py:39:    sys.stdout.reconfigure(encoding="utf-8")
./phase05_final_test.py:45:import config
./phase05_final_test.py:128:    p1 = config.RESULTS_DIR / "01_baseline_berturk" / "metrics.json"
./phase05_final_test.py:141:    p3 = config.RESULTS_DIR / "03_defense" / "comparison.json"
./phase05_final_test.py:184:                "confusion": b["confusion"],
./phase05_final_test.py:187:                # reported per slice. Recompute from `confusion` if ever needed
./phase05_final_test.py:195:                                          "n", "support_off", "confusion")},
./phase05_final_test.py:203:        # Selective prediction, only where confidences exist. The keyword filter
./phase05_final_test.py:204:        # has no notion of confidence, so it has no risk-coverage curve -- that
./phase05_final_test.py:321:    ap.add_argument("--model", default=config.MODEL_NAME if hasattr(config, "MODEL_NAME")
./phase05_final_test.py:324:    ap.add_argument("--max_len", type=int, default=config.MAX_LEN)
./phase05_final_test.py:325:    ap.add_argument("--seed", type=int, default=config.SEED)
./phase05_final_test.py:332:    if config.TEST_SPEND_RECORD.exists():
./phase05_final_test.py:334:                 f"({config.TEST_SPEND_RECORD}).")
./phase05_final_test.py:336:    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
./phase05_final_test.py:346:        args.calibration or config.RESULTS_DIR / "04_calibration" / "calibration.json")
./phase05_final_test.py:361:    hashes = {"test_sha256": data_io.sha256(config.COLTEKIN_TEST),
./phase05_final_test.py:362:              "gold_sha256": data_io.sha256(config.COLTEKIN_GOLD),
./phase05_final_test.py:363:              "lexicon_sha256": data_io.sha256(config.LEXICON_PATH)}
./phase05_final_test.py:452:    config.TEST_SPEND_RECORD.parent.mkdir(parents=True, exist_ok=True)
./phase05_final_test.py:453:    config.TEST_SPEND_RECORD.write_text(json.dumps(spend, indent=2), encoding="utf-8")
./phase05_final_test.py:455:    print(f"TEST SET MARKED SPENT -> {config.TEST_SPEND_RECORD}")
./phase05_paired_deltas.py:26:    sys.stdout.reconfigure(encoding="utf-8")
./phase05_paired_deltas.py:32:import config
./phase05_paired_deltas.py:44:    ap.add_argument("--seed", type=int, default=config.SEED)
./phase05_paired_deltas.py:47:    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
./phase08_lexical_analysis.py:28:import config
./phase08_lexical_analysis.py:250:        sys.stdout.reconfigure(encoding="utf-8")
./phase08_lexical_analysis.py:254:    out_dir = config.RESULTS_DIR / "08_lexical_analysis"
./phase08_lexical_analysis.py:262:    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
./phase08_lexical_analysis.py:263:    all_rows = data_io.load_coltekin_train(config.COLTEKIN_TRAIN)
./phase08_lexical_analysis.py:264:    split_path = config.SPLITS_DIR / "split_seed42.json"
./phase08_lexical_analysis.py:266:        all_rows, split_path, train_sha, seed=config.SEED,
./phase08_lexical_analysis.py:267:        dev_fraction=config.DEV_FRACTION)
./phase08_lexical_analysis.py:270:    lex_list = lexicon.load_lexicon(config.LEXICON_PATH)
./phase08_lexical_analysis.py:277:          f"sha {data_io.sha256(config.LEXICON_PATH)[:16]}")
./phase08_lexical_analysis.py:375:    tags = json.loads((config.RESULTS_DIR / "02_failure_analysis" /
./phase08_lexical_analysis.py:478:    # and cannot confirm anything; it is here because the composition of group 2
./phase08_lexical_analysis.py:553:    # length context, since it is the obvious confound
./phase08_lexical_analysis.py:575:            "lexicon_sha256": data_io.sha256(config.LEXICON_PATH),
./phase08_lexical_analysis.py:625:                        "confirmatory; subsets are the assistant's semantic judgment "
./phase09_stage1_auc.py:36:import config                                    # noqa: E402
./phase09_stage1_auc.py:239:        r["p_off"] = float(r["confidence"])
./phase09_stage1_auc.py:535:    lex_list = lexicon.load_lexicon(config.LEXICON_PATH)
./report/build_docx.py:44:# configuration
./report/build_docx.py:678:    sys.stdout.reconfigure(encoding="utf-8")
./src/calibration.py:10:    and it does not change the ORDER of rows by confidence.
./src/calibration.py:11:  * SELECTIVE PREDICTION uses that order to defer the least confident rows to a
./src/calibration.py:64:    confidence is unrecoverable from the dump (C4-5).
./src/calibration.py:73:def decision_confidence(p_off):
./src/calibration.py:81:    Bins are equal-width over the confidence range [0.5, 1.0]. Empty bins are
./src/calibration.py:94:             "n": 0, "correct": 0, "conf_sum": 0.0} for i in range(n_bins)]
./src/calibration.py:97:        conf = decision_confidence(p)
./src/calibration.py:99:        idx = int((conf - lo) / width)
./src/calibration.py:100:        if idx >= n_bins:          # conf == 1.0 lands one past the last bin
./src/calibration.py:107:        b["conf_sum"] += conf
./src/calibration.py:111:        b["mean_confidence"] = (b["conf_sum"] / b["n"]) if b["n"] else None
./src/calibration.py:112:        b["gap"] = ((b["accuracy"] - b["mean_confidence"])
./src/calibration.py:114:        del b["conf_sum"]
./src/calibration.py:121:    `signed_gap` = mean(accuracy - confidence) weighted by bin size. Its SIGN is
./src/calibration.py:122:    the answer to "over- or under-confident": negative means confidence exceeds
./src/calibration.py:123:    accuracy, i.e. overconfident. ECE alone is unsigned and cannot say which.
./src/calibration.py:207:    """Row indices sorted most-confident first. Ties broken by index so the
./src/calibration.py:210:                  key=lambda i: (-decision_confidence(p_off[i]), i))
./src/calibration.py:216:    At coverage c the c most-confident rows are answered automatically and the
./src/calibration.py:240:            "threshold": decision_confidence(p_off[order[k - 1]]),
./src/calibration.py:253:    return decision_confidence(p_off[order[k - 1]])
./src/calibration.py:264:        (auto if decision_confidence(p) >= threshold else deferred).append(i)
./src/calibration.py:332:    conf = [decision_confidence(p) for p in p_off]
./src/calibration.py:339:        keep = [i for i in idx if conf[i] >= threshold]
./src/data_io.py:177:    import config
./src/data_io.py:179:    dev_fraction = config.DEV_FRACTION if dev_fraction is None else dev_fraction
./src/data_io.py:180:    seed = config.SEED if seed is None else seed
./src/data_io.py:212:    import config
./src/data_io.py:214:    seed = config.SEED if seed is None else seed
./src/data_io.py:336:    import config
./src/data_io.py:338:    seed = config.SEED if seed is None else seed
./src/data_io.py:339:    dev_fraction = config.DEV_FRACTION if dev_fraction is None else dev_fraction
./src/data_io.py:357:# convenience loaders (paths come from config, never from a caller's literal)
./src/data_io.py:363:    import config
./src/data_io.py:365:    path = Path(path or config.COLTEKIN_TRAIN)
./src/data_io.py:390:    import config
./src/data_io.py:395:    if config.TEST_SPEND_RECORD.exists():
./src/data_io.py:396:        spent = json.loads(config.TEST_SPEND_RECORD.read_text(encoding="utf-8"))
./src/data_io.py:402:            f"  record     : {config.TEST_SPEND_RECORD}\n\n"
./src/data_io.py:414:        config.TEST_OPEN_LOG.parent.mkdir(parents=True, exist_ok=True)
./src/data_io.py:416:        if config.TEST_OPEN_LOG.exists():
./src/data_io.py:417:            log = json.loads(config.TEST_OPEN_LOG.read_text(encoding="utf-8"))
./src/data_io.py:420:        config.TEST_OPEN_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")
./src/data_io.py:424:            f"Cannot write the test-set open log at {config.TEST_OPEN_LOG}. "
./src/data_io.py:428:    path = Path(path or config.COLTEKIN_TEST)
./src/data_io.py:429:    gold_path = Path(gold_path or config.COLTEKIN_GOLD)
./src/evaluate.py:91:        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
./src/lexicon.py:40:        import config
./src/lexicon.py:42:        path = config.LEXICON_PATH
./src/models.py:5:Single configuration -- no hyperparameter search (phase 01 says a sweep costs a
./src/models.py:61:    """Versions + device, recorded in run_config.json. A result that cannot be
./src/models.py:344:                "config": {"model_name": model_name, "lr": lr, "batch_size": batch_size,
./src/phase11_prior_correction.py:19:C11-3, stated once here because the confusion it guards against is the easiest
./src/phase11_prior_correction.py:22:quantity -- it bins on decision confidence `max(p, 1-p)` over both classes and
./src/phase11_prior_correction.py:47:import config                                      # noqa: E402
./src/phase11_prior_correction.py:109:# C11-3: the statistics. Binned on P(OFF), NOT on decision confidence.
./src/phase11_prior_correction.py:167:    Positive means the model **under**-states P(OFF) -- under-confidence in the
./src/phase11_prior_correction.py:366:                                   (config.LEXICON_PATH, LEXICON_SHA256, LEXICON_BYTES,
./src/phase11_prior_correction.py:381:        r["p_off"] = float(r["confidence"])
./src/phase11_prior_correction.py:393:    g.add("rows violating `pred == OFF iff confidence > 0.5`", 0, viol)
./src/phase11_prior_correction.py:394:    g.add("rows with confidence == 0.5 exactly", 0, sum(1 for r in rows
./src/phase11_prior_correction.py:431:        lex = lexicon.load_lexicon(config.LEXICON_PATH)
./src/phase11_prior_correction.py:469:    rates 57.8% vs 13.6%). Raw confusion counts are retained."""
./src/phase11_prior_correction.py:481:        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
./src/phase11_prior_correction.py:482:        "confusion_note": "raw counts only; per-slice macro-F1 and per-slice accuracy are "
./src/phase11_prior_correction.py:626:            "C11-1 preamble: Surana's subgroups are OVER-confident (false positives on "
./src/phase11_prior_correction.py:655:            "lexicon": str(Path(config.LEXICON_PATH).relative_to(ROOT)).replace("\\", "/"),
./src/phase11_prior_correction.py:660:            "score_column": "confidence",
./src/phase11_prior_correction.py:662:            "frozen_decision_rule": "pred == OFF iff confidence > 0.5 (asserted, not assumed)",
./src/phase11_prior_correction.py:670:                               "under-confidence in the OFF direction.",
./src/phase11_prior_correction.py:673:                "bins on decision confidence max(p, 1-p) over both classes and returned a "
./src/phase11_prior_correction.py:674:                "global signed gap of -0.0091 with direction `overconfident` and "
./src/phase11_prior_correction.py:801:    print("    POLARITY: Surana's subgroups are OVER-confident; our hypothesis is")
./src/phase12_threshold_policy.py:27:    phase-01 constraint). Raw confusion counts, OFF-recall and OFF-precision
./src/phase12_threshold_policy.py:50:import config                                                       # noqa: E402
./src/phase12_threshold_policy.py:239:# systems, scoring, confusion
./src/phase12_threshold_policy.py:260:def confusion(rows, flag):
./src/phase12_threshold_policy.py:279:    those two statistics are not comparable across them. Raw confusion counts,
./src/phase12_threshold_policy.py:283:    cf = confusion(rows, flag)
./src/phase12_threshold_policy.py:287:           "confusion": cf,
./src/phase12_threshold_policy.py:295:        c = confusion(sub, sf)
./src/phase12_threshold_policy.py:297:            "confusion": c,
./src/phase12_threshold_policy.py:505:    c1b = confusion(eval_rows, f1b)
./src/phase12_threshold_policy.py:506:    c2 = confusion(eval_rows, f2)
./src/phase12_threshold_policy.py:542:        "S1b": {"cost": cost_1b, "confusion": c1b},
./src/phase12_threshold_policy.py:543:        "S2": {"cost": cost_2, "confusion": c2},
./src/phase12_threshold_policy.py:560:    records as a spec defect because it leaves the base-rate confound intact.
./src/phase12_threshold_policy.py:613:            "confusion": desc["confusion"],
./src/phase12_threshold_policy.py:703:    lex = lexicon.load_lexicon(config.LEXICON_PATH)
./src/phase12_threshold_policy.py:720:    if d_s0["confusion"] != d_s1a["confusion"]:
./src/phase12_threshold_policy.py:721:        sys.exit(f"ABORT (C12-4): at r=1 S1a does not reproduce S0's EVAL confusion "
./src/phase12_threshold_policy.py:722:                 f"counts. S0={d_s0['confusion']} S1a={d_s1a['confusion']}")
./src/phase12_threshold_policy.py:724:          f"S0's EVAL confusion counts {d_s0['confusion']}")
./src/phase12_threshold_policy.py:739:          f"FP={primary['S1b']['confusion']['fp']} FN={primary['S1b']['confusion']['fn']}")
./src/phase12_threshold_policy.py:741:          f"FP={primary['S2']['confusion']['fp']} FN={primary['S2']['confusion']['fn']}")
./src/phase12_threshold_policy.py:778:            print(f"  {r:>3} {name:>4} {b['cost']:>9.6f} {b['confusion']['fp']:>5} "
./src/phase12_threshold_policy.py:779:                  f"{b['confusion']['fn']:>5} {b['confusion']['n_flagged']:>6} "
./src/phase12_threshold_policy.py:925:            "S1a_reproduces_S0_eval_confusion": d_s0["confusion"] == d_s1a["confusion"],
./src/phase12_threshold_policy.py:926:            "confusion": d_s0["confusion"],
./tests/test_calibration.py:7:    deliberately overconfident data must come back > 1;
./tests/test_calibration.py:29:    0/1 without changing the labels -- i.e. overconfidence.
./tests/test_calibration.py:77:def test_fit_exceeds_one_on_overconfident_data():
./tests/test_calibration.py:85:def test_fit_below_one_on_underconfident_data():
./tests/test_calibration.py:96:def test_ece_signed_gap_negative_when_overconfident():
./tests/test_calibration.py:97:    """Overconfident => confidence exceeds accuracy => accuracy-confidence < 0."""
./tests/test_calibration.py:124:    """Deferring the least confident rows should not make the kept set worse."""
./tests/test_data_io.py:1:"""Sanity checks for the confirmed data-format traps.
./tests/test_demo.py:98:               "keyword": {"decision": "NOT", "confidence": None,
./tests/test_demo.py:100:               "raw": {"decision": "OFF", "confidence": 0.9, "detail": "P(OFF) = 0.9"},
./tests/test_demo.py:101:               "1a1b_d": {"decision": "OFF", "confidence": 0.8, "detail": "P(OFF) = 0.8"}},
./tests/test_demo.py:102:           "selective": {"confidence": 0.9, "threshold": 0.6632,
./tests/test_lexical_analysis.py:118:    assert r["diff_unmatched"] > 0.15          # the confound, unadjusted
./tests/test_phase11_verdict.py:24:statistic, which bins on decision confidence `max(p, 1-p)` over both classes.
./tests/test_phase11_verdict.py:79:    Positive means the model under-states P(OFF) -- under-confidence in the OFF
./tests/test_split_and_metrics.py:115:    assert s["confusion"] == {"tp": 1, "fn": 1, "fp": 0, "tn": 2}
./tests/test_split_and_metrics.py:254:    (d / "run_config.json").write_text('{"run_id": "01_baseline_berturk"}', encoding="utf-8")
./tests/test_split_and_metrics.py:255:    (d / "dev_predictions.csv").write_text("row_id,text,gold,pred,confidence,slice\n1,a,OFF,OFF,0.9,lexicon_hit\n",
./tests/test_split_and_metrics.py:269:                                      "results_log_row.md", "run_config.json",
./tests/test_stage1b_defense_auc.py:183:        w.writerow(["row_id", "text", "gold", "pred", "confidence", "slice"])
./tests/test_stage1_auc.py:118:def test_verdict_confirms_only_above_the_large_threshold_with_a_positive_interval():
./tests/test_test_set_guard.py:20:import config
./tests/test_test_set_guard.py:27:    monkeypatch.setattr(config, "TEST_OPEN_LOG", tmp_path / "opened.json")
./tests/test_test_set_guard.py:28:    monkeypatch.setattr(config, "TEST_SPEND_RECORD", tmp_path / "spent.json")
./tests/test_test_set_guard.py:29:    monkeypatch.setattr(config, "COLTEKIN_TEST", tmp_path / "missing_test.tsv")
./tests/test_test_set_guard.py:30:    monkeypatch.setattr(config, "COLTEKIN_GOLD", tmp_path / "missing_gold.tsv")
./tests/test_test_set_guard.py:37:    assert not config.TEST_OPEN_LOG.exists(), "a refused call must not count as an open"
./tests/test_test_set_guard.py:41:    config.TEST_SPEND_RECORD.write_text(json.dumps({
./tests/test_test_set_guard.py:47:    assert not config.TEST_OPEN_LOG.exists(), "a refused call must not count as an open"
./tests/test_test_set_guard.py:51:    config.TEST_SPEND_RECORD.write_text(json.dumps({
./tests/test_test_set_guard.py:69:    assert config.TEST_OPEN_LOG.exists(), "open log must precede the read"
./tests/test_test_set_guard.py:70:    log = json.loads(config.TEST_OPEN_LOG.read_text(encoding="utf-8"))
./tests/test_test_set_guard.py:78:    log = json.loads(config.TEST_OPEN_LOG.read_text(encoding="utf-8"))
./tests/test_test_set_guard.py:89:    fresh = importlib.reload(config)
./tests/test_test_set_guard.py:95:        importlib.reload(config)
./tests/_dryrun_phase01_outputs.py:28:  random   -- seeded coin flips. Non-degenerate confusion matrices, a non-zero
./tests/_dryrun_phase01_outputs.py:44:import config  # noqa: E402
./tests/_dryrun_phase01_outputs.py:94:                      "run_config.json", "results_log_row.md"]
./tests/_dryrun_phase01_outputs.py:106:        c = b["confusion"]
./tests/_dryrun_phase01_outputs.py:118:    assert rows[0] == "row_id,text,gold,pred,confidence,slice"
./tests/_dryrun_phase01_outputs.py:137:    canonical = Path(config.RESULTS_DIR / drv.RUN_ID).resolve()
./tests/_dryrun_phase04.py:35:        # boundary path. `sharpen` then makes the dump overconfident by a known
./tests/_dryrun_phase04.py:45:            "confidence": f"{p:.6f}",
./tests/_dryrun_phase04.py:50:                                          "confidence", "slice"])
./tests/_dryrun_phase05.py:72:    assert "selective" not in systems["keyword"], "keyword filter has no confidences"
```

## 2. `grep -rn "max(p" --include=*.py`

Exit code 0. 11 matching lines.

```
./demo/app.py:143:    conf = max(p, 1.0 - p)
./demo/app.py:262:  decision confidence max(p, 1-p) = <code>{sel['confidence']:.4f}</code>,
./handoff_bundle/demo/app.py:143:    conf = max(p, 1.0 - p)
./handoff_bundle/demo/app.py:262:  decision confidence max(p, 1-p) = <code>{sel['confidence']:.4f}</code>,
./phase04_calibration.py:10:  C4-2  ECE over 15 equal-width bins on max(p, 1-p), with 10/20-bin sensitivity
./phase09_stage1_auc.py:192:        j = int(np.nanargmax(prec))
./src/calibration.py:74:    """Confidence in the decision actually made, i.e. max(p, 1-p) in [0.5, 1]."""
./src/calibration.py:75:    return max(p_off, 1.0 - p_off)
./src/phase11_prior_correction.py:22:quantity -- it bins on decision confidence `max(p, 1-p)` over both classes and
./src/phase11_prior_correction.py:673:                "bins on decision confidence max(p, 1-p) over both classes and returned a "
./tests/test_phase11_verdict.py:24:statistic, which bins on decision confidence `max(p, 1-p)` over both classes.
```

## 3. `calibration.json` — full contents, verbatim

Path relative to repo root: `results/04_calibration/calibration.json`

Size: 46790 bytes. Newline-terminated lines: 1451. Trailing newline: no.

```json
{
  "run_id": "04_calibration",
  "generated_at": "2026-08-16T10:40:43",
  "seed": 42,
  "n_boot": 1000,
  "dev_fingerprint": "034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4",
  "official_test_set_touched": false,
  "protocol": "phases/04_calibration.md (C4-1..C4-8)",
  "coverage_grid": [
    1.0,
    0.95,
    0.9,
    0.85,
    0.8,
    0.75,
    0.7,
    0.65,
    0.6,
    0.55,
    0.5
  ],
  "baseline_identity_check": "phase-01 dump is identical to run_raw",
  "variants": {
    "raw": {
      "variant": "raw",
      "source": "/content/drive/MyDrive/nsosyal-bstar/results/03_defense/run_raw/dev_predictions.csv",
      "n_dev": 4764,
      "dev_fingerprint": "034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4",
      "n_cal": 2382,
      "n_eval": 2382,
      "saturated_rows": {
        "dev": 0,
        "cal": 0,
        "eval": 0,
        "note": "P(OFF) dumped at 6dp; 0.000000/1.000000 clipped to 5e-7 and counted."
      },
      "temperature_fit": {
        "temperature": 0.9948165193869881,
        "nll_before": 0.26164312590326666,
        "nll_after": 0.26163936785454145,
        "n_fit": 2382,
        "grid_best": 1.0,
        "search_lo": 0.05,
        "search_hi": 20.0,
        "at_boundary": false
      },
      "ece": {
        "before": {
          "10": {
            "ece": 0.01618815449202298,
            "mce": 0.11744255118110247,
            "signed_gap": -0.009073424013433562,
            "n": 2382,
            "n_bins": 10
          },
          "15": {
            "ece": 0.02053844164567604,
            "mce": 0.11843494594594595,
            "signed_gap": -0.009073424013434063,
            "n": 2382,
            "n_bins": 15
          },
          "20": {
            "ece": 0.020611647355163815,
            "mce": 0.16293859090909102,
            "signed_gap": -0.009073424013434148,
            "n": 2382,
            "n_bins": 20
          }
        },
        "after": {
          "10": {
            "ece": 0.01540522837113413,
            "mce": 0.1258849415608061,
            "signed_gap": -0.009663465409713353,
            "n": 2382,
            "n_bins": 10
          },
          "15": {
            "ece": 0.019074118554954684,
            "mce": 0.12295188508860555,
            "signed_gap": -0.009663465409712938,
            "n": 2382,
            "n_bins": 15
          },
          "20": {
            "ece": 0.02112985484106817,
            "mce": 0.16218789370725573,
            "signed_gap": -0.00966346540971262,
            "n": 2382,
            "n_bins": 20
          }
        }
      },
      "reliability": {
        "before": [
          {
            "lo": 0.5,
            "hi": 0.5333333333333333,
            "n": 43,
            "correct": 23,
            "accuracy": 0.5348837209302325,
            "mean_confidence": 0.5185912093023254,
            "gap": 0.016292511627907125
          },
          {
            "lo": 0.5333333333333333,
            "hi": 0.5666666666666667,
            "n": 37,
            "correct": 16,
            "accuracy": 0.43243243243243246,
            "mean_confidence": 0.5508673783783784,
            "gap": -0.11843494594594595
          },
          {
            "lo": 0.5666666666666667,
            "hi": 0.6,
            "n": 43,
            "correct": 29,
            "accuracy": 0.6744186046511628,
            "mean_confidence": 0.5869052558139537,
            "gap": 0.08751334883720907
          },
          {
            "lo": 0.6,
            "hi": 0.6333333333333333,
            "n": 46,
            "correct": 29,
            "accuracy": 0.6304347826086957,
            "mean_confidence": 0.6148485217391305,
            "gap": 0.01558626086956516
          },
          {
            "lo": 0.6333333333333333,
            "hi": 0.6666666666666666,
            "n": 45,
            "correct": 30,
            "accuracy": 0.6666666666666666,
            "mean_confidence": 0.6505402000000001,
            "gap": 0.016126466666666506
          },
          {
            "lo": 0.6666666666666666,
            "hi": 0.7,
            "n": 49,
            "correct": 32,
            "accuracy": 0.6530612244897959,
            "mean_confidence": 0.6817264285714284,
            "gap": -0.028665204081632534
          },
          {
            "lo": 0.7,
            "hi": 0.7333333333333334,
            "n": 42,
            "correct": 32,
            "accuracy": 0.7619047619047619,
            "mean_confidence": 0.7176210000000002,
            "gap": 0.04428376190476169
          },
          {
            "lo": 0.7333333333333334,
            "hi": 0.7666666666666666,
            "n": 59,
            "correct": 46,
            "accuracy": 0.7796610169491526,
            "mean_confidence": 0.7504746101694915,
            "gap": 0.02918640677966111
          },
          {
            "lo": 0.7666666666666666,
            "hi": 0.8,
            "n": 72,
            "correct": 55,
            "accuracy": 0.7638888888888888,
            "mean_confidence": 0.7842372222222225,
            "gap": -0.020348333333333635
          },
          {
            "lo": 0.8,
            "hi": 0.8333333333333333,
            "n": 82,
            "correct": 58,
            "accuracy": 0.7073170731707317,
            "mean_confidence": 0.8173123902439025,
            "gap": -0.10999531707317078
          },
          {
            "lo": 0.8333333333333333,
            "hi": 0.8666666666666667,
            "n": 91,
            "correct": 68,
            "accuracy": 0.7472527472527473,
            "mean_confidence": 0.8508853076923081,
            "gap": -0.10363256043956082
          },
          {
            "lo": 0.8666666666666667,
            "hi": 0.9,
            "n": 112,
            "correct": 97,
            "accuracy": 0.8660714285714286,
            "mean_confidence": 0.8842075982142859,
            "gap": -0.018136169642857247
          },
          {
            "lo": 0.9,
            "hi": 0.9333333333333333,
            "n": 170,
            "correct": 160,
            "accuracy": 0.9411764705882353,
            "mean_confidence": 0.9170982529411764,
            "gap": 0.024078217647058864
          },
          {
            "lo": 0.9333333333333333,
            "hi": 0.9666666666666667,
            "n": 369,
            "correct": 344,
            "accuracy": 0.9322493224932249,
            "mean_confidence": 0.9526681138211384,
            "gap": -0.020418791327913466
          },
          {
            "lo": 0.9666666666666667,
            "hi": 1.0,
            "n": 1122,
            "correct": 1105,
            "accuracy": 0.9848484848484849,
            "mean_confidence": 0.9847831443850266,
            "gap": 6.534046345829658e-05
          }
        ],
        "after": [
          {
            "lo": 0.5,
            "hi": 0.5333333333333333,
            "n": 43,
            "correct": 23,
            "accuracy": 0.5348837209302325,
            "mean_confidence": 0.5186879395419338,
            "gap": 0.01619578138829869
          },
          {
            "lo": 0.5333333333333333,
            "hi": 0.5666666666666667,
            "n": 37,
            "correct": 16,
            "accuracy": 0.43243243243243246,
            "mean_confidence": 0.5511303561617661,
            "gap": -0.11869792372933363
          },
          {
            "lo": 0.5666666666666667,
            "hi": 0.6,
            "n": 42,
            "correct": 29,
            "accuracy": 0.6904761904761905,
            "mean_confidence": 0.5870431189794696,
            "gap": 0.10343307149672087
          },
          {
            "lo": 0.6,
            "hi": 0.6333333333333333,
            "n": 46,
            "correct": 28,
            "accuracy": 0.6086956521739131,
            "mean_confidence": 0.614694338264363,
            "gap": -0.005998686090449956
          },
          {
            "lo": 0.6333333333333333,
            "hi": 0.6666666666666666,
            "n": 46,
            "correct": 31,
            "accuracy": 0.6739130434782609,
            "mean_confidence": 0.6508951152210173,
            "gap": 0.02301792825724358
          },
          {
            "lo": 0.6666666666666666,
            "hi": 0.7,
            "n": 46,
            "correct": 31,
            "accuracy": 0.6739130434782609,
            "mean_confidence": 0.6814178710093582,
            "gap": -0.00750482753109738
          },
          {
            "lo": 0.7,
            "hi": 0.7333333333333334,
            "n": 43,
            "correct": 31,
            "accuracy": 0.7209302325581395,
            "mean_confidence": 0.716639295196733,
            "gap": 0.0042909373614065105
          },
          {
            "lo": 0.7333333333333334,
            "hi": 0.7666666666666666,
            "n": 59,
            "correct": 46,
            "accuracy": 0.7796610169491526,
            "mean_confidence": 0.7504075843622728,
            "gap": 0.029253432586879735
          },
          {
            "lo": 0.7666666666666666,
            "hi": 0.8,
            "n": 69,
            "correct": 54,
            "accuracy": 0.782608695652174,
            "mean_confidence": 0.783736498563206,
            "gap": -0.0011278029110320942
          },
          {
            "lo": 0.8,
            "hi": 0.8333333333333333,
            "n": 85,
            "correct": 59,
            "accuracy": 0.6941176470588235,
            "mean_confidence": 0.8170695321474291,
            "gap": -0.12295188508860555
          },
          {
            "lo": 0.8333333333333333,
            "hi": 0.8666666666666667,
            "n": 89,
            "correct": 67,
            "accuracy": 0.7528089887640449,
            "mean_confidence": 0.8509425031401613,
            "gap": -0.09813351437611639
          },
          {
            "lo": 0.8666666666666667,
            "hi": 0.9,
            "n": 110,
            "correct": 95,
            "accuracy": 0.8636363636363636,
            "mean_confidence": 0.8837860305614557,
            "gap": -0.020149666925092014
          },
          {
            "lo": 0.9,
            "hi": 0.9333333333333333,
            "n": 171,
            "correct": 160,
            "accuracy": 0.935672514619883,
            "mean_confidence": 0.9169696329565835,
            "gap": 0.018702881663299475
          },
          {
            "lo": 0.9333333333333333,
            "hi": 0.9666666666666667,
            "n": 368,
            "correct": 344,
            "accuracy": 0.9347826086956522,
            "mean_confidence": 0.9528739495695927,
            "gap": -0.018091340873940487
          },
          {
            "lo": 0.9666666666666667,
            "hi": 1.0,
            "n": 1128,
            "correct": 1110,
            "accuracy": 0.9840425531914894,
            "mean_confidence": 0.9849971537953062,
            "gap": -0.000954600603816802
          }
        ]
      },
      "direction": "overconfident",
      "risk_coverage": [
        {
          "target_coverage": 1.0,
          "coverage": 1.0,
          "n_auto": 4764,
          "n_deferred": 0,
          "macro_f1": 0.8270752670616224,
          "error_rate": 0.10453400503778337,
          "errors": 498,
          "off_recall": 0.6902173913043478,
          "off_precision": 0.7488207547169812,
          "threshold": 0.501639
        },
        {
          "target_coverage": 0.95,
          "coverage": 0.9500419815281276,
          "n_auto": 4526,
          "n_deferred": 238,
          "macro_f1": 0.8466512411102995,
          "error_rate": 0.08793636765355722,
          "errors": 398,
          "off_recall": 0.7009569377990431,
          "off_precision": 0.7983651226158038,
          "threshold": 0.593018
        },
        {
          "target_coverage": 0.9,
          "coverage": 0.9000839630562553,
          "n_auto": 4288,
          "n_deferred": 476,
          "macro_f1": 0.8620662641989312,
          "error_rate": 0.07392723880597014,
          "errors": 317,
          "off_recall": 0.7142857142857143,
          "off_precision": 0.8306962025316456,
          "threshold": 0.672032
        },
        {
          "target_coverage": 0.85,
          "coverage": 0.8499160369437447,
          "n_auto": 4049,
          "n_deferred": 715,
          "macro_f1": 0.8713554960126241,
          "error_rate": 0.06446036058285996,
          "errors": 261,
          "off_recall": 0.7238689547581904,
          "off_precision": 0.8467153284671532,
          "threshold": 0.7527820000000001
        },
        {
          "target_coverage": 0.8,
          "coverage": 0.7999580184718724,
          "n_auto": 3811,
          "n_deferred": 953,
          "macro_f1": 0.8927359763054825,
          "error_rate": 0.05116767252689583,
          "errors": 195,
          "off_recall": 0.7583774250440917,
          "off_precision": 0.8811475409836066,
          "threshold": 0.811083
        },
        {
          "target_coverage": 0.75,
          "coverage": 0.75,
          "n_auto": 3573,
          "n_deferred": 1191,
          "macro_f1": 0.9070245017381062,
          "error_rate": 0.04086202071088721,
          "errors": 146,
          "off_recall": 0.7720739219712526,
          "off_precision": 0.9148418491484185,
          "threshold": 0.855162
        },
        {
          "target_coverage": 0.7,
          "coverage": 0.7000419815281276,
          "n_auto": 3335,
          "n_deferred": 1429,
          "macro_f1": 0.9222405579843842,
          "error_rate": 0.032083958020989505,
          "errors": 107,
          "off_recall": 0.8057553956834532,
          "off_precision": 0.9281767955801105,
          "threshold": 0.889203
        },
        {
          "target_coverage": 0.65,
          "coverage": 0.6500839630562553,
          "n_auto": 3097,
          "n_deferred": 1667,
          "macro_f1": 0.925165415413838,
          "error_rate": 0.02970616725863739,
          "errors": 92,
          "off_recall": 0.8108108108108109,
          "off_precision": 0.9316770186335404,
          "threshold": 0.916832
        },
        {
          "target_coverage": 0.6,
          "coverage": 0.5999160369437447,
          "n_auto": 2858,
          "n_deferred": 1906,
          "macro_f1": 0.9354193212274898,
          "error_rate": 0.025192442267319804,
          "errors": 72,
          "off_recall": 0.8343373493975904,
          "off_precision": 0.9421768707482994,
          "threshold": 0.935812
        },
        {
          "target_coverage": 0.55,
          "coverage": 0.5499580184718724,
          "n_auto": 2620,
          "n_deferred": 2144,
          "macro_f1": 0.9438106493380425,
          "error_rate": 0.021755725190839695,
          "errors": 57,
          "off_recall": 0.847682119205298,
          "off_precision": 0.9588014981273408,
          "threshold": 0.949385
        },
        {
          "target_coverage": 0.5,
          "coverage": 0.5,
          "n_auto": 2382,
          "n_deferred": 2382,
          "macro_f1": 0.9496689058090311,
          "error_rate": 0.019311502938706968,
          "errors": 46,
          "off_recall": 0.8629629629629629,
          "off_precision": 0.9628099173553719,
          "threshold": 0.960248
        }
      ],
      "rc_invariance_check": {
        "holds": true,
        "max_abs_diff": 0.0,
        "temperature": 0.9948165193869881
      },
      "operating_points": {
        "high_automation": {
          "threshold": 0.663171,
          "coverage": 0.9118387909319899,
          "n_auto": 2172,
          "n_deferred": 210,
          "macro_f1": 0.8504158585200146,
          "error_rate": 0.07918968692449356,
          "errors_auto": 172,
          "off_recall": 0.6692913385826772,
          "off_precision": 0.8471760797342193,
          "deferred_error_rate": 0.4095238095238095,
          "errors_deferred": 86,
          "errors_total": 258,
          "capture_lift": 3.780952380952381,
          "error_capture_share": 0.3333333333333333,
          "by_slice": {
            "lexicon_free": {
              "n_rows": 2073,
              "share_of_dev": 0.8702770780856424,
              "n_deferred": 188,
              "deferral_rate": 0.09068982151471297,
              "share_of_deferrals": 0.8952380952380953,
              "errors_deferred": 75,
              "errors_auto": 142,
              "auto_error_rate": 0.0753315649867374,
              "deferred_error_rate": 0.39893617021276595,
              "errors_total": 217,
              "error_capture_share": 0.3456221198156682
            },
            "lexicon_hit": {
              "n_rows": 309,
              "share_of_dev": 0.1297229219143577,
              "n_deferred": 22,
              "deferral_rate": 0.07119741100323625,
              "share_of_deferrals": 0.10476190476190476,
              "errors_deferred": 11,
              "errors_auto": 30,
              "auto_error_rate": 0.10452961672473868,
              "deferred_error_rate": 0.5,
              "errors_total": 41,
              "error_capture_share": 0.2682926829268293
            }
          },
          "ci": {
            "coverage": {
              "ci_low": 0.9005037783375315,
              "ci_high": 0.9235936188077246
            },
            "macro_f1": {
              "ci_low": 0.8286904200612458,
              "ci_high": 0.8720922794288068
            },
            "error_rate": {
              "ci_low": 0.06806472675590995,
              "ci_high": 0.08994193035109556
            },
            "n_boot_used": 1000
          },
          "target_coverage": 0.9,
          "threshold_selected_on": "CAL",
          "metrics_measured_on": "EVAL",
          "rule": "fixed at 90% coverage, declared in advance"
        },
        "high_precision": {
          "threshold": 0.80091,
          "coverage": 0.8161209068010076,
          "n_auto": 1944,
          "n_deferred": 438,
          "macro_f1": 0.8755804766152671,
          "error_rate": 0.058127572016460904,
          "errors_auto": 113,
          "off_recall": 0.7152777777777778,
          "off_precision": 0.869198312236287,
          "deferred_error_rate": 0.3310502283105023,
          "errors_deferred": 145,
          "errors_total": 258,
          "capture_lift": 3.056440479983009,
          "error_capture_share": 0.562015503875969,
          "by_slice": {
            "lexicon_free": {
              "n_rows": 2073,
              "share_of_dev": 0.8702770780856424,
              "n_deferred": 373,
              "deferral_rate": 0.1799324650265316,
              "share_of_deferrals": 0.8515981735159818,
              "errors_deferred": 122,
              "errors_auto": 95,
              "auto_error_rate": 0.05588235294117647,
              "deferred_error_rate": 0.32707774798927614,
              "errors_total": 217,
              "error_capture_share": 0.5622119815668203
            },
            "lexicon_hit": {
              "n_rows": 309,
              "share_of_dev": 0.1297229219143577,
              "n_deferred": 65,
              "deferral_rate": 0.21035598705501618,
              "share_of_deferrals": 0.14840182648401826,
              "errors_deferred": 23,
              "errors_auto": 18,
              "auto_error_rate": 0.07377049180327869,
              "deferred_error_rate": 0.35384615384615387,
              "errors_total": 41,
              "error_capture_share": 0.5609756097560976
            }
          },
          "ci": {
            "coverage": {
              "ci_low": 0.800997061293031,
              "ci_high": 0.832924013434089
            },
            "macro_f1": {
              "ci_low": 0.8522377638077904,
              "ci_high": 0.8963198012605136
            },
            "error_rate": {
              "ci_low": 0.04812997504435943,
              "ci_high": 0.06836756497470788
            },
            "n_boot_used": 1000
          },
          "target_coverage": 0.8,
          "threshold_selected_on": "CAL",
          "metrics_measured_on": "EVAL",
          "rule": "largest grid coverage whose CAL error rate <= 5.0%"
        }
      },
      "deferral_full_dev": {
        "high_automation": {
          "threshold": 0.663171,
          "coverage": 0.9059613769941226,
          "n_auto": 4316,
          "n_deferred": 448,
          "macro_f1": 0.8590025041934549,
          "error_rate": 0.07645968489341984,
          "errors_auto": 330,
          "off_recall": 0.7087765957446809,
          "off_precision": 0.827639751552795,
          "deferred_error_rate": 0.375,
          "errors_deferred": 168,
          "errors_total": 498,
          "capture_lift": 3.587349397590361,
          "error_capture_share": 0.3373493975903614,
          "by_slice": {
            "lexicon_free": {
              "n_rows": 4150,
              "share_of_dev": 0.8711167086481948,
              "n_deferred": 389,
              "deferral_rate": 0.09373493975903614,
              "share_of_deferrals": 0.8683035714285714,
              "errors_deferred": 144,
              "errors_auto": 269,
              "auto_error_rate": 0.07152353097580431,
              "deferred_error_rate": 0.37017994858611825,
              "errors_total": 413,
              "error_capture_share": 0.3486682808716707
            },
            "lexicon_hit": {
              "n_rows": 614,
              "share_of_dev": 0.1288832913518052,
              "n_deferred": 59,
              "deferral_rate": 0.09609120521172639,
              "share_of_deferrals": 0.13169642857142858,
              "errors_deferred": 24,
              "errors_auto": 61,
              "auto_error_rate": 0.10990990990990991,
              "deferred_error_rate": 0.4067796610169492,
              "errors_total": 85,
              "error_capture_share": 0.2823529411764706
            }
          }
        },
        "high_precision": {
          "threshold": 0.80091,
          "coverage": 0.808144416456759,
          "n_auto": 3850,
          "n_deferred": 914,
          "macro_f1": 0.8891794646774902,
          "error_rate": 0.053246753246753244,
          "errors_auto": 205,
          "off_recall": 0.75,
          "off_precision": 0.8787878787878788,
          "deferred_error_rate": 0.32056892778993434,
          "errors_deferred": 293,
          "errors_total": 498,
          "capture_lift": 3.0666473333157573,
          "error_capture_share": 0.5883534136546185,
          "by_slice": {
            "lexicon_free": {
              "n_rows": 4150,
              "share_of_dev": 0.8711167086481948,
              "n_deferred": 772,
              "deferral_rate": 0.18602409638554218,
              "share_of_deferrals": 0.8446389496717724,
              "errors_deferred": 245,
              "errors_auto": 168,
              "auto_error_rate": 0.0497335701598579,
              "deferred_error_rate": 0.3173575129533679,
              "errors_total": 413,
              "error_capture_share": 0.5932203389830508
            },
            "lexicon_hit": {
              "n_rows": 614,
              "share_of_dev": 0.1288832913518052,
              "n_deferred": 142,
              "deferral_rate": 0.23127035830618892,
              "share_of_deferrals": 0.15536105032822758,
              "errors_deferred": 48,
              "errors_auto": 37,
              "auto_error_rate": 0.07838983050847458,
              "deferred_error_rate": 0.3380281690140845,
              "errors_total": 85,
              "error_capture_share": 0.5647058823529412
            }
          }
        }
      }
    },
    "1a1b_d": {
      "variant": "1a1b_d",
      "source": "/content/drive/MyDrive/nsosyal-bstar/results/03_defense/run_1a1b_d/dev_predictions.csv",
      "n_dev": 4764,
      "dev_fingerprint": "034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4",
      "n_cal": 2382,
      "n_eval": 2382,
      "saturated_rows": {
        "dev": 0,
        "cal": 0,
        "eval": 0,
        "note": "P(OFF) dumped at 6dp; 0.000000/1.000000 clipped to 5e-7 and counted."
      },
      "temperature_fit": {
        "temperature": 1.9731501284219068,
        "nll_before": 0.38310494726301275,
        "nll_after": 0.2914050836130504,
        "n_fit": 2382,
        "grid_best": 2.114742526881128,
        "search_lo": 0.05,
        "search_hi": 20.0,
        "at_boundary": false
      },
      "ece": {
        "before": {
          "10": {
            "ece": 0.07725658270361054,
            "mce": 0.292989742857143,
            "signed_gap": -0.07390538958858114,
            "n": 2382,
            "n_bins": 10
          },
          "15": {
            "ece": 0.07856318219983208,
            "mce": 0.3487243636363636,
            "signed_gap": -0.07390538958858102,
            "n": 2382,
            "n_bins": 15
          },
          "20": {
            "ece": 0.0784024710327457,
            "mce": 0.40719999999999995,
            "signed_gap": -0.07390538958858113,
            "n": 2382,
            "n_bins": 20
          }
        },
        "after": {
          "10": {
            "ece": 0.02956129536472367,
            "mce": 0.21304601567285136,
            "signed_gap": -0.009037278549136768,
            "n": 2382,
            "n_bins": 10
          },
          "15": {
            "ece": 0.026965557911279803,
            "mce": 0.2056489049992538,
            "signed_gap": -0.009037278549136631,
            "n": 2382,
            "n_bins": 15
          },
          "20": {
            "ece": 0.03128775470852991,
            "mce": 0.23806698155763573,
            "signed_gap": -0.009037278549136437,
            "n": 2382,
            "n_bins": 20
          }
        }
      },
      "reliability": {
        "before": [
          {
            "lo": 0.5,
            "hi": 0.5333333333333333,
            "n": 16,
            "correct": 11,
            "accuracy": 0.6875,
            "mean_confidence": 0.5175167500000001,
            "gap": 0.16998324999999992
          },
          {
            "lo": 0.5333333333333333,
            "hi": 0.5666666666666667,
            "n": 18,
            "correct": 12,
            "accuracy": 0.6666666666666666,
            "mean_confidence": 0.5520689444444444,
            "gap": 0.1145977222222222
          },
          {
            "lo": 0.5666666666666667,
            "hi": 0.6,
            "n": 21,
            "correct": 11,
            "accuracy": 0.5238095238095238,
            "mean_confidence": 0.5832576190476191,
            "gap": -0.059448095238095244
          },
          {
            "lo": 0.6,
            "hi": 0.6333333333333333,
            "n": 12,
            "correct": 7,
            "accuracy": 0.5833333333333334,
            "mean_confidence": 0.6166526666666666,
            "gap": -0.033319333333333256
          },
          {
            "lo": 0.6333333333333333,
            "hi": 0.6666666666666666,
            "n": 10,
            "correct": 5,
            "accuracy": 0.5,
            "mean_confidence": 0.6496152000000001,
            "gap": -0.14961520000000006
          },
          {
            "lo": 0.6666666666666666,
            "hi": 0.7,
            "n": 21,
            "correct": 15,
            "accuracy": 0.7142857142857143,
            "mean_confidence": 0.67786,
            "gap": 0.036425714285714283
          },
          {
            "lo": 0.7,
            "hi": 0.7333333333333334,
            "n": 11,
            "correct": 4,
            "accuracy": 0.36363636363636365,
            "mean_confidence": 0.7123607272727273,
            "gap": -0.3487243636363636
          },
          {
            "lo": 0.7333333333333334,
            "hi": 0.7666666666666666,
            "n": 20,
            "correct": 9,
            "accuracy": 0.45,
            "mean_confidence": 0.7515825,
            "gap": -0.30158250000000003
          },
          {
            "lo": 0.7666666666666666,
            "hi": 0.8,
            "n": 26,
            "correct": 14,
            "accuracy": 0.5384615384615384,
            "mean_confidence": 0.7847016923076923,
            "gap": -0.24624015384615383
          },
          {
            "lo": 0.8,
            "hi": 0.8333333333333333,
            "n": 24,
            "correct": 16,
            "accuracy": 0.6666666666666666,
            "mean_confidence": 0.8193045833333333,
            "gap": -0.1526379166666667
          },
          {
            "lo": 0.8333333333333333,
            "hi": 0.8666666666666667,
            "n": 30,
            "correct": 17,
            "accuracy": 0.5666666666666667,
            "mean_confidence": 0.8512716999999999,
            "gap": -0.2846050333333332
          },
          {
            "lo": 0.8666666666666667,
            "hi": 0.9,
            "n": 45,
            "correct": 33,
            "accuracy": 0.7333333333333333,
            "mean_confidence": 0.8847472444444444,
            "gap": -0.15141391111111113
          },
          {
            "lo": 0.9,
            "hi": 0.9333333333333333,
            "n": 51,
            "correct": 35,
            "accuracy": 0.6862745098039216,
            "mean_confidence": 0.9191075882352943,
            "gap": -0.2328330784313727
          },
          {
            "lo": 0.9333333333333333,
            "hi": 0.9666666666666667,
            "n": 119,
            "correct": 94,
            "accuracy": 0.7899159663865546,
            "mean_confidence": 0.953266218487395,
            "gap": -0.16335025210084042
          },
          {
            "lo": 0.9666666666666667,
            "hi": 1.0,
            "n": 1958,
            "correct": 1835,
            "accuracy": 0.9371807967313586,
            "mean_confidence": 0.9943041670071502,
            "gap": -0.05712337027579162
          }
        ],
        "after": [
          {
            "lo": 0.5,
            "hi": 0.5333333333333333,
            "n": 33,
            "correct": 22,
            "accuracy": 0.6666666666666666,
            "mean_confidence": 0.517719242473161,
            "gap": 0.1489474241935056
          },
          {
            "lo": 0.5333333333333333,
            "hi": 0.5666666666666667,
            "n": 33,
            "correct": 19,
            "accuracy": 0.5757575757575758,
            "mean_confidence": 0.5478013019955139,
            "gap": 0.02795627376206189
          },
          {
            "lo": 0.5666666666666667,
            "hi": 0.6,
            "n": 31,
            "correct": 19,
            "accuracy": 0.6129032258064516,
            "mean_confidence": 0.5871239219354236,
            "gap": 0.025779303871028003
          },
          {
            "lo": 0.6,
            "hi": 0.6333333333333333,
            "n": 18,
            "correct": 9,
            "accuracy": 0.5,
            "mean_confidence": 0.6176949662960838,
            "gap": -0.11769496629608378
          },
          {
            "lo": 0.6333333333333333,
            "hi": 0.6666666666666666,
            "n": 36,
            "correct": 16,
            "accuracy": 0.4444444444444444,
            "mean_confidence": 0.6500933494436982,
            "gap": -0.2056489049992538
          },
          {
            "lo": 0.6666666666666666,
            "hi": 0.7,
            "n": 34,
            "correct": 23,
            "accuracy": 0.6764705882352942,
            "mean_confidence": 0.6837268984537033,
            "gap": -0.007256310218409112
          },
          {
            "lo": 0.7,
            "hi": 0.7333333333333334,
            "n": 39,
            "correct": 23,
            "accuracy": 0.5897435897435898,
            "mean_confidence": 0.7168025524641857,
            "gap": -0.1270589627205959
          },
          {
            "lo": 0.7333333333333334,
            "hi": 0.7666666666666666,
            "n": 46,
            "correct": 32,
            "accuracy": 0.6956521739130435,
            "mean_confidence": 0.748828780411733,
            "gap": -0.053176606498689494
          },
          {
            "lo": 0.7666666666666666,
            "hi": 0.8,
            "n": 46,
            "correct": 33,
            "accuracy": 0.717391304347826,
            "mean_confidence": 0.7847890691133207,
            "gap": -0.06739776476549464
          },
          {
            "lo": 0.8,
            "hi": 0.8333333333333333,
            "n": 74,
            "correct": 60,
            "accuracy": 0.8108108108108109,
            "mean_confidence": 0.8184663526412348,
            "gap": -0.00765554183042394
          },
          {
            "lo": 0.8333333333333333,
            "hi": 0.8666666666666667,
            "n": 117,
            "correct": 97,
            "accuracy": 0.8290598290598291,
            "mean_confidence": 0.852062096191075,
            "gap": -0.023002267131245868
          },
          {
            "lo": 0.8666666666666667,
            "hi": 0.9,
            "n": 156,
            "correct": 128,
            "accuracy": 0.8205128205128205,
            "mean_confidence": 0.8858283740361339,
            "gap": -0.06531555352331342
          },
          {
            "lo": 0.9,
            "hi": 0.9333333333333333,
            "n": 321,
            "correct": 286,
            "accuracy": 0.8909657320872274,
            "mean_confidence": 0.9195080105293697,
            "gap": -0.0285422784421423
          },
          {
            "lo": 0.9333333333333333,
            "hi": 0.9666666666666667,
            "n": 1196,
            "correct": 1149,
            "accuracy": 0.9607023411371237,
            "mean_confidence": 0.953509953140129,
            "gap": 0.007192387996994731
          },
          {
            "lo": 0.9666666666666667,
            "hi": 1.0,
            "n": 202,
            "correct": 202,
            "accuracy": 1.0,
            "mean_confidence": 0.9697351276070731,
            "gap": 0.030264872392926856
          }
        ]
      },
      "direction": "overconfident",
      "risk_coverage": [
        {
          "target_coverage": 1.0,
          "coverage": 1.0,
          "n_auto": 4764,
          "n_deferred": 0,
          "macro_f1": 0.820163145136936,
          "error_rate": 0.11041141897565071,
          "errors": 526,
          "off_recall": 0.6945652173913044,
          "off_precision": 0.7228506787330317,
          "threshold": 0.503605
        },
        {
          "target_coverage": 0.95,
          "coverage": 0.9500419815281276,
          "n_auto": 4526,
          "n_deferred": 238,
          "macro_f1": 0.83411271070298,
          "error_rate": 0.0958904109589041,
          "errors": 434,
          "off_recall": 0.7067484662576687,
          "off_precision": 0.7470817120622568,
          "threshold": 0.738754
        },
        {
          "target_coverage": 0.9,
          "coverage": 0.9000839630562553,
          "n_auto": 4288,
          "n_deferred": 476,
          "macro_f1": 0.8538757703998193,
          "error_rate": 0.07905783582089553,
          "errors": 339,
          "off_recall": 0.729050279329609,
          "off_precision": 0.782608695652174,
          "threshold": 0.881749
        },
        {
          "target_coverage": 0.85,
          "coverage": 0.8499160369437447,
          "n_auto": 4049,
          "n_deferred": 715,
          "macro_f1": 0.8683576169398475,
          "error_rate": 0.0674240553223018,
          "errors": 273,
          "off_recall": 0.753577106518283,
          "off_precision": 0.8006756756756757,
          "threshold": 0.947504
        },
        {
          "target_coverage": 0.8,
          "coverage": 0.7999580184718724,
          "n_auto": 3811,
          "n_deferred": 953,
          "macro_f1": 0.8836491428420545,
          "error_rate": 0.05825242718446602,
          "errors": 222,
          "off_recall": 0.7791304347826087,
          "off_precision": 0.8250460405156538,
          "threshold": 0.971865
        },
        {
          "target_coverage": 0.75,
          "coverage": 0.75,
          "n_auto": 3573,
          "n_deferred": 1191,
          "macro_f1": 0.8952437073990497,
          "error_rate": 0.050937587461516935,
          "errors": 182,
          "off_recall": 0.7950191570881227,
          "off_precision": 0.8469387755102041,
          "threshold": 0.983382
        },
        {
          "target_coverage": 0.7,
          "coverage": 0.7000419815281276,
          "n_auto": 3335,
          "n_deferred": 1429,
          "macro_f1": 0.9037896669289274,
          "error_rate": 0.046176911544227886,
          "errors": 154,
          "off_recall": 0.8066528066528067,
          "off_precision": 0.8641425389755011,
          "threshold": 0.988746
        },
        {
          "target_coverage": 0.65,
          "coverage": 0.6500839630562553,
          "n_auto": 3097,
          "n_deferred": 1667,
          "macro_f1": 0.9197373616338826,
          "error_rate": 0.03842428156280271,
          "errors": 119,
          "off_recall": 0.8393665158371041,
          "off_precision": 0.8854415274463007,
          "threshold": 0.991799
        },
        {
          "target_coverage": 0.6,
          "coverage": 0.5999160369437447,
          "n_auto": 2858,
          "n_deferred": 1906,
          "macro_f1": 0.926059807799251,
          "error_rate": 0.035339398180545836,
          "errors": 101,
          "off_recall": 0.858560794044665,
          "off_precision": 0.8871794871794871,
          "threshold": 0.993755
        },
        {
          "target_coverage": 0.55,
          "coverage": 0.5499580184718724,
          "n_auto": 2620,
          "n_deferred": 2144,
          "macro_f1": 0.9324348718583505,
          "error_rate": 0.03244274809160305,
          "errors": 85,
          "off_recall": 0.8659517426273459,
          "off_precision": 0.9022346368715084,
          "threshold": 0.995083
        },
        {
          "target_coverage": 0.5,
          "coverage": 0.5,
          "n_auto": 2382,
          "n_deferred": 2382,
          "macro_f1": 0.9379392998992577,
          "error_rate": 0.030226700251889168,
          "errors": 72,
          "off_recall": 0.877906976744186,
          "off_precision": 0.9096385542168675,
          "threshold": 0.995919
        }
      ],
      "rc_invariance_check": {
        "holds": true,
        "max_abs_diff": 0.0,
        "temperature": 1.9731501284219068
      },
      "operating_points": {
        "high_automation": {
          "threshold": 0.865618,
          "coverage": 0.9139378673383711,
          "n_auto": 2177,
          "n_deferred": 205,
          "macro_f1": 0.8488017855620764,
          "error_rate": 0.08084519981626091,
          "errors_auto": 176,
          "off_recall": 0.7087912087912088,
          "off_precision": 0.7865853658536586,
          "deferred_error_rate": 0.4292682926829268,
          "errors_deferred": 88,
          "errors_total": 264,
          "capture_lift": 3.8731707317073165,
          "error_capture_share": 0.3333333333333333,
          "by_slice": {
            "lexicon_free": {
              "n_rows": 2073,
              "share_of_dev": 0.8702770780856424,
              "n_deferred": 168,
              "deferral_rate": 0.08104196816208394,
              "share_of_deferrals": 0.8195121951219512,
              "errors_deferred": 76,
              "errors_auto": 145,
              "auto_error_rate": 0.07611548556430446,
              "deferred_error_rate": 0.4523809523809524,
              "errors_total": 221,
              "error_capture_share": 0.3438914027149321
            },
            "lexicon_hit": {
              "n_rows": 309,
              "share_of_dev": 0.1297229219143577,
              "n_deferred": 37,
              "deferral_rate": 0.11974110032362459,
              "share_of_deferrals": 0.18048780487804877,
              "errors_deferred": 12,
              "errors_auto": 31,
              "auto_error_rate": 0.11397058823529412,
              "deferred_error_rate": 0.32432432432432434,
              "errors_total": 43,
              "error_capture_share": 0.27906976744186046
            }
          },
          "ci": {
            "coverage": {
              "ci_low": 0.9025923593618808,
              "ci_high": 0.9252833753148615
            },
            "macro_f1": {
              "ci_low": 0.8280317701221932,
              "ci_high": 0.8683886271562539
            },
            "error_rate": {
              "ci_low": 0.06984193096151185,
              "ci_high": 0.09261894478562356
            },
            "n_boot_used": 1000
          },
          "target_coverage": 0.9,
          "threshold_selected_on": "CAL",
          "metrics_measured_on": "EVAL",
          "rule": "fixed at 90% coverage, declared in advance"
        },
        "high_precision": {
          "threshold": 0.987655,
          "coverage": 0.7178841309823678,
          "n_auto": 1710,
          "n_deferred": 672,
          "macro_f1": 0.8980868943322009,
          "error_rate": 0.04736842105263158,
          "errors_auto": 81,
          "off_recall": 0.7907949790794979,
          "off_precision": 0.8590909090909091,
          "deferred_error_rate": 0.27232142857142855,
          "errors_deferred": 183,
          "errors_total": 264,
          "capture_lift": 2.457081980519481,
          "error_capture_share": 0.6931818181818182,
          "by_slice": {
            "lexicon_free": {
              "n_rows": 2073,
              "share_of_dev": 0.8702770780856424,
              "n_deferred": 574,
              "deferral_rate": 0.2768933912204534,
              "share_of_deferrals": 0.8541666666666666,
              "errors_deferred": 155,
              "errors_auto": 66,
              "auto_error_rate": 0.044029352901934625,
              "deferred_error_rate": 0.2700348432055749,
              "errors_total": 221,
              "error_capture_share": 0.7013574660633484
            },
            "lexicon_hit": {
              "n_rows": 309,
              "share_of_dev": 0.1297229219143577,
              "n_deferred": 98,
              "deferral_rate": 0.31715210355987056,
              "share_of_deferrals": 0.14583333333333334,
              "errors_deferred": 28,
              "errors_auto": 15,
              "auto_error_rate": 0.07109004739336493,
              "deferred_error_rate": 0.2857142857142857,
              "errors_total": 43,
              "error_capture_share": 0.6511627906976745
            }
          },
          "ci": {
            "coverage": {
              "ci_low": 0.6998320738874895,
              "ci_high": 0.7363664987405542
            },
            "macro_f1": {
              "ci_low": 0.8774663965406154,
              "ci_high": 0.9188115595047089
            },
            "error_rate": {
              "ci_low": 0.037744098297656695,
              "ci_high": 0.057512581360151506
            },
            "n_boot_used": 1000
          },
          "target_coverage": 0.7,
          "threshold_selected_on": "CAL",
          "metrics_measured_on": "EVAL",
          "rule": "largest grid coverage whose CAL error rate <= 5.0%"
        }
      },
      "deferral_full_dev": {
        "high_automation": {
          "threshold": 0.865618,
          "coverage": 0.9070109151973131,
          "n_auto": 4321,
          "n_deferred": 443,
          "macro_f1": 0.8520277644739429,
          "error_rate": 0.08076834066188382,
          "errors_auto": 349,
          "off_recall": 0.7270233196159122,
          "off_precision": 0.7794117647058824,
          "deferred_error_rate": 0.39954853273137697,
          "errors_deferred": 177,
          "errors_total": 526,
          "capture_lift": 3.6187247337115585,
          "error_capture_share": 0.3365019011406844,
          "by_slice": {
            "lexicon_free": {
              "n_rows": 4150,
              "share_of_dev": 0.8711167086481948,
              "n_deferred": 366,
              "deferral_rate": 0.08819277108433735,
              "share_of_deferrals": 0.8261851015801355,
              "errors_deferred": 144,
              "errors_auto": 279,
              "auto_error_rate": 0.07373150105708245,
              "deferred_error_rate": 0.39344262295081966,
              "errors_total": 423,
              "error_capture_share": 0.3404255319148936
            },
            "lexicon_hit": {
              "n_rows": 614,
              "share_of_dev": 0.1288832913518052,
              "n_deferred": 77,
              "deferral_rate": 0.1254071661237785,
              "share_of_deferrals": 0.17381489841986456,
              "errors_deferred": 33,
              "errors_auto": 70,
              "auto_error_rate": 0.1303538175046555,
              "deferred_error_rate": 0.42857142857142855,
              "errors_total": 103,
              "error_capture_share": 0.32038834951456313
            }
          }
        },
        "high_precision": {
          "threshold": 0.987655,
          "coverage": 0.7088581024349286,
          "n_auto": 3377,
          "n_deferred": 1387,
          "macro_f1": 0.9018329648799219,
          "error_rate": 0.047379330766952915,
          "errors_auto": 160,
          "off_recall": 0.8008130081300813,
          "off_precision": 0.8640350877192983,
          "deferred_error_rate": 0.2638788752703677,
          "errors_deferred": 366,
          "errors_total": 526,
          "capture_lift": 2.3899600033993,
          "error_capture_share": 0.6958174904942965,
          "by_slice": {
            "lexicon_free": {
              "n_rows": 4150,
              "share_of_dev": 0.8711167086481948,
              "n_deferred": 1184,
              "deferral_rate": 0.2853012048192771,
              "share_of_deferrals": 0.8536409516943042,
              "errors_deferred": 297,
              "errors_auto": 126,
              "auto_error_rate": 0.04248145650708024,
              "deferred_error_rate": 0.25084459459459457,
              "errors_total": 423,
              "error_capture_share": 0.7021276595744681
            },
            "lexicon_hit": {
              "n_rows": 614,
              "share_of_dev": 0.1288832913518052,
              "n_deferred": 203,
              "deferral_rate": 0.3306188925081433,
              "share_of_deferrals": 0.14635904830569574,
              "errors_deferred": 69,
              "errors_auto": 34,
              "auto_error_rate": 0.0827250608272506,
              "deferred_error_rate": 0.3399014778325123,
              "errors_total": 103,
              "error_capture_share": 0.6699029126213593
            }
          }
        }
      }
    }
  },
  "defense_vs_raw": {
    "temperature": {
      "raw": 0.9948165193869881,
      "1a1b_d": 1.9731501284219068
    },
    "ece_before_15": {
      "raw": 0.02053844164567604,
      "1a1b_d": 0.07856318219983208
    },
    "ece_after_15": {
      "raw": 0.019074118554954684,
      "1a1b_d": 0.026965557911279803
    },
    "delta_ece_before_15": 0.05802474055415603
  }
}
```

## 4. Checkpoint manifest / sha256 record

**The file exists.** Path relative to repo root: `demo_assets/manifest.json`, 1305 bytes.

It is **not in the repository**: `demo_assets/` is gitignored at `.gitignore:56`. It exists on this machine's disk only, written by `demo/build_assets.py`.

```json
{
  "built_at": "2026-08-23T01:33:15",
  "model_name": "dbmdz/bert-base-turkish-cased",
  "note": "Everything demo/app.py needs. Built once with network; the demo itself sets HF_HUB_OFFLINE=1 and never fetches.",
  "total_bytes": 885850309,
  "files": {
    "checkpoints/1a1b_d.pt": {
      "bytes": 442544192,
      "sha256": "81781e33af0cfbae7c405a19847f298a8938d5fd02ca2147876217ee17153549"
    },
    "checkpoints/raw.pt": {
      "bytes": 442544192,
      "sha256": "43a20d5525aff0a57c0bda2be559a5acdf84848cf7cbed844f0c8f5f3024d4ca"
    },
    "lexicon/karaliste.txt": {
      "bytes": 5988,
      "sha256": "0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b"
    },
    "operating_point.json": {
      "bytes": 287,
      "sha256": "5d7a4355b84e4484e443679f50a7cdb604462b7456035b1c2ca0848a7782b8c0"
    },
    "tokenizer/config.json": {
      "bytes": 738,
      "sha256": "980b01ddb94ee8cc2533e064bdca97584b96bbf9755601217ae3d13460c58f48"
    },
    "tokenizer/tokenizer.json": {
      "bytes": 754526,
      "sha256": "d424e0bceb7f017dfced77157d14647505b28b41bfc8d9bffd5631f1b1fe61e5"
    },
    "tokenizer/tokenizer_config.json": {
      "bytes": 386,
      "sha256": "d50873edfa649e9950fbfb196da01d0b2b4470a25e2ac711cf5c7022761b0a04"
    }
  }
}
```

## 5. `demo/app.py` lines 49-88 — `clean_input`, full body

```python
def clean_input(raw):
    """Make any input safe to run, and say what was done to it.

    Returns (text, notes). Never raises: the demo has to survive an empty box,
    a pasted novel, an emoji wall and English, because all four will happen.
    """
    notes = []
    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raw = str(raw)

    # Strip control characters (except tab/newline) -- pasted text from PDFs and
    # terminals carries them and they break the tokenizer's assumptions.
    cleaned = "".join(c for c in raw
                      if c in "\t\n" or not unicodedata.category(c).startswith("C"))
    if cleaned != raw:
        notes.append("removed control characters")

    cleaned = cleaned.strip()
    if len(cleaned) > MAX_CHARS:
        cleaned = cleaned[:MAX_CHARS]
        notes.append(f"truncated to {MAX_CHARS} characters")

    if not cleaned:
        return "", ["empty input -- nothing to classify"]

    # Text with no letters or digits at all (emoji only, punctuation only) is
    # accepted and classified, but flagged: the model has essentially nothing to
    # work with and its confidence should not be read as meaningful.
    if not any(c.isalnum() for c in cleaned):
        notes.append("no alphanumeric characters -- the model has no lexical "
                     "signal here and its confidence is not meaningful")
    return cleaned, notes


# --------------------------------------------------------------------------
# the three systems
# --------------------------------------------------------------------------

```

## 6. `demo/app.py` lines 110-160 — `model_decision` and `classify`, full bodies

```python
def model_decision(name, text):
    import torch

    tok, model = STATE["tokenizer"], STATE["models"][name]
    enc = tok([text], truncation=True, max_length=MAX_LEN,
              padding=True, return_tensors="pt")
    enc = {k: v.to(STATE["device"]) for k, v in enc.items()}
    with torch.no_grad():
        logits = model(**enc).logits[0]
        p_off = float(torch.softmax(logits, dim=-1)[1])
    return ("OFF" if p_off >= 0.5 else "NOT"), p_off


def classify(raw):
    """Everything the page shows for one input."""
    text, notes = clean_input(raw)
    if not text:
        return {"ok": False, "notes": notes, "text": ""}

    kw, hits = keyword_decision(text, STATE["lexicon"])
    out = {"ok": True, "text": text, "notes": notes,
           "n_chars": len(text), "n_tokens": len(STATE["tokenizer"].tokenize(text)),
           "systems": {"keyword": {"decision": kw, "confidence": None,
                                   "detail": ("lexicon roots matched: " + ", ".join(hits))
                                   if hits else "no lexicon root matched"}}}
    for name in ("raw", "1a1b_d"):
        d, p = model_decision(name, text)
        out["systems"][name] = {"decision": d, "confidence": p,
                                "detail": f"P(OFF) = {p:.4f}"}

    # Selective prediction uses the RAW model at the frozen phase-04 threshold.
    op = STATE["operating_point"]
    p = out["systems"]["raw"]["confidence"]
    conf = max(p, 1.0 - p)
    auto = conf >= op["threshold"]
    out["selective"] = {
        "confidence": conf,
        "threshold": op["threshold"],
        "auto": auto,
        "route": "AUTO-RESOLVE" if auto else "DEFER TO REVIEW",
        "decision": out["systems"]["raw"]["decision"] if auto else None,
        "margin": conf - op["threshold"],
    }
    return out


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------

CSS = """
```

## Appendix — `demo/app.py` module-level structure

### Imports

```
19:import argparse
20:import html
21:import json
22:import os
23:import socketserver
24:import sys
25:import unicodedata
26:from http.server import BaseHTTPRequestHandler, HTTPServer
27:from pathlib import Path
37:from src import lexicon
111:    import torch
360:    import torch
```

### Module-level assignments

```
39:MAX_CHARS = 4000          # hard cap on accepted input; longer is truncated
40:MAX_LEN = 128             # the token budget every reported number was measured at
42:STATE = {}                # models, tokenizer, lexicon, operating point
160:CSS = """
198:JS = """
```

### Class and def signatures

```
49:def clean_input(raw):
89:def keyword_decision(text, lex):
110:def model_decision(name, text):
123:def classify(raw):
218:def render_result(res):
271:def render_page():
320:class Handler(BaseHTTPRequestHandler):
323:    def log_message(self, fmt, *a):        # keep the console readable
326:    def _send(self, body, ctype="text/html; charset=utf-8", code=200):
334:    def do_GET(self):
340:    def do_POST(self):
354:class Server(socketserver.ThreadingMixIn, HTTPServer):
359:def load_assets(assets):
397:def main():
```

### Route / server dispatch

```
26:from http.server import BaseHTTPRequestHandler, HTTPServer
320:class Handler(BaseHTTPRequestHandler):
328:        self.send_response(code)
334:    def do_GET(self):
335:        if self.path in ("/", "/index.html"):
340:    def do_POST(self):
341:        if self.path != "/api/classify":
354:class Server(socketserver.ThreadingMixIn, HTTPServer):
435:            httpd.serve_forever()
```

### Checkpoint paths as they literally appear

```
292:<div class="sub">Runs fully offline. Local checkpoints only, no network calls.
364:    missing = [p for p in ("tokenizer", "checkpoints/raw.pt",
365:                           "checkpoints/1a1b_d.pt", "lexicon/karaliste.txt",
380:        state = torch.load(assets / "checkpoints" / f"{name}.pt",
382:        m.load_state_dict(state["model"])
```

### Checkpoint paths — `demo/build_assets.py` and `config.py`

`demo/build_assets.py`:

```
14:Usage (on the machine that has network + the checkpoints):
16:        --raw_ckpt     <drive>/checkpoints/01_baseline_berturk/best.pt \
17:        --defense_ckpt <drive>/checkpoints/03_defense/1a1b_d/best.pt \
46:    ap.add_argument("--raw_ckpt", required=True)
47:    ap.add_argument("--defense_ckpt", required=True)
54:    (out / "checkpoints").mkdir(parents=True, exist_ok=True)
69:    # --- checkpoints -------------------------------------------------------
72:    for name, src in (("raw", args.raw_ckpt), ("1a1b_d", args.defense_ckpt)):
73:        dst = out / "checkpoints" / f"{name}.pt"
```

`config.py`:

```
16:NSOSYAL_CKPT  overrides the checkpoint directory (same reason)
42:# ends -- results and checkpoints must be able to point at Drive instead.
45:# Model checkpoints. Gitignored (see .gitignore): they are reproducible from a
48:CKPT_DIR = Path(os.getenv("NSOSYAL_CKPT", ROOT / "checkpoints"))
```
