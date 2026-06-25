import sys
sys.path.insert(0, "D:/github/dash_temporal")
from analise_temporal.services import dados

dff = dados.df_mov.copy()
base = dff.dropna(subset=["ano", "representante_governo"]).copy()
base["ano"] = base["ano"].astype(int)

# Check unique governments per year
for ano in sorted(base["ano"].unique()):
    govs = base[base["ano"] == ano]["representante_governo"].unique()
    if len(govs) > 1:
        print(f"{ano}: MULTIPLOS governos -> {list(govs)}")
    else:
        print(f"{ano}: {list(govs)[0]}")

# Specifically check governador_edicao for 2013 and 2015
for ano in [2013, 2015]:
    sub = base[base["ano"] == ano]
    print(f"\n{ano} - total records: {len(sub)}")
    for gov in sub["representante_governo"].unique():
        qtd = len(sub[sub["representante_governo"] == gov])
        print(f"  {gov}: {qtd}")
