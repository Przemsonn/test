# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
# ---

# %% [markdown]
# # Uczenie maszynowe – lab 11: Sieci konwolucyjne
#
# Jeden skrypt realizujący po kolei wszystkie zadania:
#   * Zad. 1   – adversarial attack na ConvNeXt_Tiny (optymalizujemy PIKSELE, nie wagi)
#   * Zad. 2.1 – klasyfikator piwa (transfer learning)
#   * Zad. 2.2 – lokalizator piwa (klasyfikacja + bbox + pewność)
#   * Zad. 3   – agent DQN do gry w Breakout (uczenie ze wzmacnianiem)
#
# UWAGA: sprawdzarka NIE uruchamia tego pliku — sprawdza obecność plików wynikowych.
# Skrypt trzeba uruchomić samodzielnie (najlepiej na GPU), żeby je wygenerować.
# Najpierw wgraj do repo pliki wynikowe, a `lab11.py` commituj na końcu
# (sprawdzenie startuje tylko przy modyfikacji `lab11.py`).

# %%
import torch
import torch.nn as nn
import pandas as pd

# --- Zad. 0: wybór urządzenia (zgodnie z tip-em z instrukcji) ---
if torch.backends.mps.is_available():
    device = torch.device("mps")
elif torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")
print(f"Urządzenie: {device}")

# Flagi pozwalające uruchamiać zadania pojedynczo (domyślnie wszystkie).
RUN_TASK1 = True   # adversarial attack
RUN_TASK2 = True   # klasyfikator + lokalizator piwa
RUN_TASK3 = True   # agent RL (Breakout)

# Stałe normalizacji ImageNet (na nich trenowany jest ConvNeXt).
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


# %% [markdown]
# ## Zadanie 1 — "Czy ten kot to... toster?" (adversarial attack)
#
# Odwracamy zwykły trening: parametrem optimizera jest **tensor obrazów**, a nie wagi.
# Zamrażamy model i tak modyfikujemy piksele, by zwracał z góry zaplanowaną klasę.

# %%
if RUN_TASK1:
    from torchvision.models import convnext_tiny, ConvNeXt_Tiny_Weights
    from umtools.datasets import load_cats
    from umtools.utils import save_image, simulate_png

    # --- model z wagami ImageNet, ZAMROŻONY ---
    weights = ConvNeXt_Tiny_Weights.DEFAULT
    categories = weights.meta["categories"]   # lista 1000 nazw klas; indeks = class_id
    preprocess = weights.transforms()         # resize + normalizacja wymagane przez model

    model = convnext_tiny(weights=weights).eval().to(device)
    for p in model.parameters():
        p.requires_grad_(False)               # NIE optymalizujemy wag

    # --- dane: zdjęcia kotów + docelowe (błędne) NAZWY klas ---
    cats = load_cats()
    cats.mosaic()
    imgs, labels = cats                       # imgs: (n,224,224,3) uint8; labels: nazwy klas

    # Model działa na indeksach -> nazwę klasy mapujemy na class_id z `categories`.
    name_to_idx = {name: i for i, name in enumerate(categories)}
    targets = torch.tensor([name_to_idx[str(n)] for n in labels], device=device)

    # (n,224,224,3) uint8 -> (n,3,224,224), a następnie preprocessing modelu.
    img_uint8 = torch.from_numpy(imgs).permute(0, 3, 1, 2).contiguous()
    img_batch = preprocess(img_uint8).clone().detach().to(device)   # znormalizowany batch

    # Gradienty mają płynąć DO PIKSELI — to one są "parametrem".
    img_batch.requires_grad_(True)

    optimizer = torch.optim.Adam([img_batch], lr=0.01)
    loss_fn = nn.CrossEntropyLoss()           # ta sama strata co przy klasyfikacji

    MAX_STEPS = 2000
    for step in range(MAX_STEPS):
        optimizer.zero_grad()
        logits = model(img_batch)
        loss = loss_fn(logits, targets)
        loss.backward()
        optimizer.step()

        with torch.no_grad():
            clean_preds = logits.argmax(dim=1)
            if step % 25 == 0:
                hit = int((clean_preds == targets).sum())
                print(f"[Zad.1] step {step:4d}  loss {loss.item():.4f}  trafień {hit}/{len(targets)}")

            # Cel uznajemy za osiągnięty dopiero po sprawdzeniu trwałości względem
            # kwantyzacji do uint8 (zapis PNG). simulate_png pełni rolę zbioru walidacyjnego.
            if (clean_preds == targets).all():
                robust = simulate_png(img_batch.detach(), normalized=True).to(device)
                robust_preds = model(robust).argmax(dim=1)
                if (robust_preds == targets).all():
                    print(f"[Zad.1] Cel osiągnięty (odporny na PNG) na kroku {step}.")
                    break

    # save_image na batchu sam dokłada suffix _{i} -> not_cat_0.png, not_cat_1.png, ...
    save_image(img_batch.detach().cpu(), "not_cat.png", normalized=True)
    print("[Zad.1] Zapisano pliki not_cat_*.png")


# %% [markdown]
# ## Zadanie 2 — "Barbara, podaj mi piwo!"
#
# Wspólne wczytanie danych i modelu bazowego dla 2.1 i 2.2.
#
# Format danych z `load_beer()`:
#   * beer.X        – (N,224,224,3) uint8
#   * beer.classes  – int8, -1 dla zdjęć bez piwa
#   * beer.bbox     – (N,4) float32 w formacie [cx, cy, w, h]
#   * beer.categories – {class_id: nazwa}

# %%
if RUN_TASK2:
    from copy import deepcopy
    from torch.utils.data import DataLoader, random_split, Subset
    import torchvision.transforms.v2 as v2
    from torchvision.models import convnext_tiny, ConvNeXt_Tiny_Weights
    from umtools.datasets import (
        load_beer, load_beer_test,
        BeerClassificationDataset, BeerLocalizationDataset,
    )

    beer = load_beer()
    beer.mosaic()
    n_classes = len(beer.categories)
    print(f"[Zad.2] Klasy piwa: {beer.categories}")

    weights = ConvNeXt_Tiny_Weights.DEFAULT
    base_model = convnext_tiny(weights=weights)

    # Augmentacja tylko dla treningu; walidacja = sama normalizacja (bez losowości).
    train_transform = v2.Compose([
        v2.ToImage(),
        v2.ToDtype(torch.float32, scale=True),
        v2.RandomHorizontalFlip(),
        v2.RandomRotation(15),
        v2.ColorJitter(brightness=0.3, contrast=0.3),
        v2.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])
    val_transform = v2.Compose([
        v2.ToImage(),
        v2.ToDtype(torch.float32, scale=True),
        v2.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


# %% [markdown]
# ### 2.1 — Klasyfikator piwa (transfer learning)
#
# Podmieniamy głowę klasyfikatora na `n_classes`, zamrażamy resztę, trenujemy.
# Ewaluacja na zbiorze walidacyjnym, żeby wykryć przeuczenie.

# %%
if RUN_TASK2:
    from torchmetrics.classification import MulticlassAccuracy

    # --- podział train/val: ten sam podział, ale różne transformacje ---
    base_ds = BeerClassificationDataset(beer)
    train_split, val_split = random_split(base_ds, [0.8, 0.2])
    train_set = Subset(BeerClassificationDataset(beer, transform=train_transform),
                       train_split.indices)
    val_set = Subset(BeerClassificationDataset(beer, transform=val_transform),
                     val_split.indices)
    train_loader = DataLoader(train_set, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=32, shuffle=False)

    # --- model: zamrażamy bazę, podmieniamy ostatnią warstwę klasyfikatora ---
    for p in base_model.parameters():
        p.requires_grad_(False)

    beer_classifier = deepcopy(base_model)
    in_features = beer_classifier.classifier[2].in_features            # 768 dla convnext_tiny
    beer_classifier.classifier[2] = nn.Linear(in_features, n_classes)  # nowa głowa = trenowalna
    beer_classifier = beer_classifier.to(device)

    optimizer = torch.optim.Adam(
        [p for p in beer_classifier.parameters() if p.requires_grad], lr=1e-3
    )
    loss_fn = nn.CrossEntropyLoss()
    metric = MulticlassAccuracy(num_classes=n_classes).to(device)

    NUM_EPOCHS = 15
    acc_history = []
    for epoch in range(1, NUM_EPOCHS + 1):
        # (opcjonalny fine-tuning) po kilku epokach odmrażamy ostatni blok cech.
        if epoch == 6:
            for p in beer_classifier.features[-1].parameters():
                p.requires_grad_(True)
            optimizer = torch.optim.Adam(
                [p for p in beer_classifier.parameters() if p.requires_grad], lr=1e-4
            )

        beer_classifier.train()
        for imgs, ys in train_loader:
            imgs, ys = imgs.to(device), ys.to(device)
            optimizer.zero_grad()
            loss = loss_fn(beer_classifier(imgs), ys)
            loss.backward()
            optimizer.step()

        beer_classifier.eval()
        with torch.no_grad():
            for imgs, ys in val_loader:
                imgs, ys = imgs.to(device), ys.to(device)
                metric.update(beer_classifier(imgs), ys)
            val_acc = metric.compute().item()
            metric.reset()
        acc_history.append(float(val_acc))
        print(f"[Zad.2.1] Epoch {epoch}; Val Accuracy: {val_acc:.4f}")

    # historia accuracy walidacyjnego -> lista float
    pd.to_pickle(acc_history, "clf_acc.pkl")

    # logity dla zbioru testowego -> tensor (N, n_classes)
    beer_test = load_beer_test()
    test_loader = DataLoader(
        BeerClassificationDataset(beer_test, transform=val_transform), batch_size=32
    )
    all_logits = []
    beer_classifier.eval()
    with torch.no_grad():
        for imgs, _ in test_loader:
            all_logits.append(beer_classifier(imgs.to(device)).cpu())
    pd.to_pickle(torch.cat(all_logits), "clf_preds.pkl")
    print("[Zad.2.1] Zapisano clf_acc.pkl oraz clf_preds.pkl")


# %% [markdown]
# ### 2.2 — Lokalizator piwa (3 głowy)
#
# Rozszerzamy NIEWYTRENOWANY klasyfikator (świeżo podmieniona głowa) o:
#   * głowę lokalizacji: 4 współrzędne po Sigmoid (format xyxy, pod MSELoss),
#   * głowę pewności: 1 logit (pod BCEWithLogitsLoss).
# Klasa dziedziczy po umtools.models.Localizer.

# %%
if RUN_TASK2:
    from umtools.models import Localizer
    from umtools.utils import to_coco
    from torchmetrics.classification import MulticlassAccuracy, BinaryAUROC
    from torchmetrics.detection import IntersectionOverUnion

    class BeerLocalizer(Localizer):
        def __init__(self, backbone, class_map, val_transform):
            # bbox_format="xyxy" -> ten sam format musi zwracać dataset (patrz niżej).
            super().__init__(class_map, bbox_format="xyxy", predict_preprocess=val_transform)
            C = backbone.classifier[2].in_features

            self.features = backbone.features      # mapa cech (B, C, 7, 7)
            self.avgpool = backbone.avgpool        # -> (B, C, 1, 1)
            self.classifier = backbone.classifier  # głowa klasyfikacji (działa na pooled)

            # lokalizacja: współrzędne znormalizowane do [0,1] przez Sigmoid
            self.loc_head = nn.Sequential(
                nn.Linear(C, 256), nn.ReLU(),
                nn.Linear(256, 4), nn.Sigmoid(),
            )
            # pewność: surowy logit (sigmoid robi dopiero BCEWithLogitsLoss)
            self.conf_head = nn.Sequential(
                nn.Linear(C, 256), nn.ReLU(),
                nn.Linear(256, 1),
            )

        def forward(self, x):
            feat = self.features(x)                 # (B, C, 7, 7)
            pooled = self.avgpool(feat)             # (B, C, 1, 1)
            flat = torch.flatten(pooled, 1)         # (B, C)
            class_logits = self.classifier(pooled)  # (B, n_classes)
            bbox = self.loc_head(flat)              # (B, 4) w [0,1], xyxy
            conf = self.conf_head(flat)             # (B, 1) surowy logit
            return class_logits, bbox, conf

    # backbone = świeży (niewytrenowany) klasyfikator piwa z podmienioną głową
    backbone = deepcopy(base_model)
    backbone.classifier[2] = nn.Linear(backbone.classifier[2].in_features, n_classes)

    model = BeerLocalizer(backbone, class_map=beer.categories,
                          val_transform=val_transform).to(device)

    # Dane bbox-aware. Bez augmentacji geometrycznej, by nie rozjechać boxów
    # (jeśli chcesz augmentować -> albumentations z bbox_params, które aktualizuje boxy).
    # bbox_format="xyxy" musi pasować do formatu w modelu (raw beer.bbox jest w [cx,cy,w,h]).
    loc_base = BeerLocalizationDataset(beer, bbox_format="xyxy")
    loc_train_split, loc_val_split = random_split(loc_base, [0.8, 0.2])
    loc_train = Subset(
        BeerLocalizationDataset(beer, transform=val_transform, bbox_format="xyxy"),
        loc_train_split.indices)
    loc_val = Subset(
        BeerLocalizationDataset(beer, transform=val_transform, bbox_format="xyxy"),
        loc_val_split.indices)
    loc_train_loader = DataLoader(loc_train, batch_size=32, shuffle=True)
    loc_val_loader = DataLoader(loc_val, batch_size=32, shuffle=False)

    # ------------------------------------------------------------------
    # UWAGA: dokładny format `target` z BeerLocalizationDataset pochodzi z umtools.
    # Najpewniej batch to (imgs, target), gdzie target zawiera:
    #   - etykietę klasy (int, -1 = brak piwa),
    #   - bbox xyxy znormalizowany do [0,1],
    #   - flagę obecności piwa (0/1).
    # Sprawdź jedną partię i w razie potrzeby dostosuj unpack():
    #     print(next(iter(loc_train_loader)))
    # ------------------------------------------------------------------
    def unpack(target):
        """Rozpakowuje cel do (cls[int64], box[B,4 float], present[B,1 float])."""
        if isinstance(target, dict):
            cls = target.get("labels", target.get("classes"))
            box = target.get("boxes", target.get("bbox"))
            present = target.get("conf", (torch.as_tensor(cls) >= 0).float().unsqueeze(1))
        else:  # krotka/lista
            cls, box, present = target
        cls = torch.as_tensor(cls).long()
        box = torch.as_tensor(box).float()
        present = torch.as_tensor(present).float().view(-1, 1)
        return cls, box, present

    ce = nn.CrossEntropyLoss(ignore_index=-1)  # ignoruj klasę dla zdjęć bez piwa
    mse = nn.MSELoss()
    bce = nn.BCEWithLogitsLoss()
    A_CLS, A_BOX, A_CONF = 1.0, 50.0, 1.0      # wagi strat (dobrane eksperymentalnie)

    optimizer = torch.optim.Adam(
        [p for p in model.parameters() if p.requires_grad], lr=1e-4
    )

    acc_m = MulticlassAccuracy(num_classes=n_classes).to(device)
    iou_m = IntersectionOverUnion().to(device)
    auc_m = BinaryAUROC().to(device)

    NUM_EPOCHS = 20
    loc_metrics = []
    for epoch in range(1, NUM_EPOCHS + 1):
        model.train()
        for imgs, target in loc_train_loader:
            cls, box, present = unpack(target)
            imgs, cls, box, present = (imgs.to(device), cls.to(device),
                                       box.to(device), present.to(device))
            optimizer.zero_grad()
            class_logits, bbox, conf = model(imgs)
            has_beer = present.squeeze(1) > 0.5
            loss = A_CONF * bce(conf, present)               # pewność: zawsze
            if has_beer.any():                               # klasa i box: tylko gdy jest piwo
                loss = loss + A_CLS * ce(class_logits[has_beer], cls[has_beer])
                loss = loss + A_BOX * mse(bbox[has_beer], box[has_beer])
            loss.backward()
            optimizer.step()

        # --- walidacja: Accuracy / IoU / ROCAUC ---
        model.eval()
        with torch.no_grad():
            for imgs, target in loc_val_loader:
                cls, box, present = unpack(target)
                imgs, cls, box, present = (imgs.to(device), cls.to(device),
                                           box.to(device), present.to(device))
                class_logits, bbox, conf = model(imgs)
                has_beer = present.squeeze(1) > 0.5
                if has_beer.any():
                    acc_m.update(class_logits[has_beer], cls[has_beer])
                    # to_coco przygotowuje boxy do formatu wymaganego przez IntersectionOverUnion
                    iou_m.update(to_coco(bbox[has_beer]), to_coco(box[has_beer]))
                auc_m.update(torch.sigmoid(conf).squeeze(1), present.squeeze(1).long())

            acc = acc_m.compute().item()
            iou = iou_m.compute()["iou"].item()
            auc = auc_m.compute().item()
            acc_m.reset(); iou_m.reset(); auc_m.reset()

        loc_metrics.append({"Accuracy": acc, "IoU": iou, "ROCAUC": auc})
        print(f"[Zad.2.2] Epoch {epoch}; Acc {acc:.3f}  IoU {iou:.3f}  ROCAUC {auc:.3f}")

    pd.to_pickle(loc_metrics, "loc_metrics.pkl")

    # predykcja dla 16 pierwszych zdjęć -> prediction.png
    results = model.predict(beer.X[:16], conf_threshold=0.5)
    results.save("prediction.png")

    # logity dla zbioru testowego -> (class_logits, bbox, conf)
    beer_test = load_beer_test()
    loc_test_loader = DataLoader(
        BeerLocalizationDataset(beer_test, transform=val_transform, bbox_format="xyxy"),
        batch_size=32)
    all_logits, all_bbox, all_conf = [], [], []
    model.eval()
    with torch.no_grad():
        for imgs, _ in loc_test_loader:
            logits, bbox, conf = model(imgs.to(device))   # nie model.predict(imgs)
            all_logits.append(logits.cpu()); all_bbox.append(bbox.cpu()); all_conf.append(conf.cpu())
    pd.to_pickle((torch.cat(all_logits), torch.cat(all_bbox), torch.cat(all_conf)),
                 "loc_preds.pkl")
    print("[Zad.2.2] Zapisano loc_metrics.pkl, prediction.png, loc_preds.pkl")


# %% [markdown]
# ## Zadanie 3 — "Będę grał w grę" (agent DQN / Breakout)
#
# Agent dziedziczy po umtools.models.Reinforcer. Wejście: (B, 4, 10, 10),
# wyjście: (B, n_actions). Mała mapa 10x10 -> lekka sieć konwolucyjna.

# %%
if RUN_TASK3:
    from umtools.models import Reinforcer
    from umtools.viz import Visualizer, Progress, Game

    class BreakoutAgent(Reinforcer):
        def __init__(self, **kw):
            super().__init__(**kw)   # rodzic ustawia self.n_actions
            self.net = nn.Sequential(
                nn.Conv2d(4, 32, kernel_size=3, stride=1, padding=1), nn.ReLU(),
                nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1), nn.ReLU(),
                nn.Flatten(),
                nn.LazyLinear(128), nn.ReLU(),   # Lazy -> wymiar wejścia liczony automatycznie
                nn.LazyLinear(self.n_actions),   # głowa: jedno Q na akcję
            )

        def forward(self, x):
            return self.net(x.float())           # (B, n_actions)

    # ddqn stabilizuje trening (mniejsze przeszacowanie wartości Q)
    agent = BreakoutAgent(algorithm="ddqn", gamma=0.99).to(device)

    # podgląd postępów (opcjonalny)
    viz = Visualizer().with_component(Progress(agent)).with_component(Game(agent))

    STEPS = 300_000   # RL wymaga cierpliwości; zwiększ, jeśli średnia < 5
    agent.fit(steps=STEPS, optimizer=torch.optim.Adam, lr=1e-4, watch=viz)
    agent.plot_rewards()

    # zapis całego agenta (nie tylko wag)
    torch.save(agent, "breakout.pt")

    # nagrody z 1000 epizodów (średnia musi być > 5)
    rewards = agent.play(n_episodes=1000)
    pd.to_pickle(rewards, "rewards.pkl")
    mean_r = sum(rewards) / len(rewards)
    print(f"[Zad.3] Średnia nagroda z 1000 epizodów: {mean_r:.2f} (cel: > 5)")

    # nagranie 3 epizodów -> gamer.gif (10 fps)
    watch = Game(agent)
    agent.play(n_episodes=3, watch=watch, fps=10)
    watch.save_gif("gamer.gif", fps=10)
    print("[Zad.3] Zapisano breakout.pt, rewards.pkl, gamer.gif")
