# SWaT.A12 Multilayer Cleaning Report

**Phase:** 1 — Data cleaning

## Summary

| Item | Value |
| :--- | ---: |
| Rows in | 28860 |
| Rows out | 28860 |
| Cols in | 256 |
| Cols out | 252 |
| Physical features | 82 |
| Protocol features | 162 |
| Network features | 7 |
| Total features | 251 |

## Dropped columns

- `PSH301.Alarm`
- `DPSH301.Alarm`
- `PSH501.Alarm`
- `PSL501.Alarm`

## Alarm encoding

### `LS201.Alarm`

- Non Active/Inactive (pre-impute NA count): 8
- Value counts before: `{'Inactive': 28852, 'Bad Input': 8}`

### `LS202.Alarm`

- Non Active/Inactive (pre-impute NA count): 8
- Value counts before: `{'Inactive': 28852, 'Bad Input': 8}`

### `LSL203.Alarm`

- Non Active/Inactive (pre-impute NA count): 8
- Value counts before: `{'Inactive': 28852, 'Bad Input': 8}`

### `LSLL203.Alarm`

- Non Active/Inactive (pre-impute NA count): 8
- Value counts before: `{'Active': 28843, 'Inactive': 9, 'Bad Input': 8}`

### `LS401.Alarm`

- Non Active/Inactive (pre-impute NA count): 0
- Value counts before: `{'Inactive': 28860}`

### `LSH601.Alarm`

- Non Active/Inactive (pre-impute NA count): 0
- Value counts before: `{'Inactive': 21918, 'Active': 6942}`

### `LSL601.Alarm`

- Non Active/Inactive (pre-impute NA count): 0
- Value counts before: `{'Inactive': 28857, 'Active': 3}`

### `LSH602.Alarm`

- Non Active/Inactive (pre-impute NA count): 0
- Value counts before: `{'Active': 28860}`

### `LSL602.Alarm`

- Non Active/Inactive (pre-impute NA count): 0
- Value counts before: `{'Inactive': 28860}`

### `LSH603.Alarm`

- Non Active/Inactive (pre-impute NA count): 0
- Value counts before: `{'Inactive': 28860}`

### `LSL603.Alarm`

- Non Active/Inactive (pre-impute NA count): 0
- Value counts before: `{'Active': 28860}`

## Protocol missingness (before fill)

- `writes_*` total NA: 0
- `last_value_*` total NA: 2126987

## Network

- NA cells before fill: 0
- Filled with 0: False

## NaN rates

- Before (cols with NA): `{'last_value_HMI_1_MV_004': 0.9997920997920998, 'last_value_HMI_1_MV_005': 0.9998613998613999, 'last_value_HMI_AIT201': 0.9995841995841996, 'last_value_HMI_AIT202': 0.9908177408177408, 'last_value_HMI_AIT203': 0.9995841995841996, 'last_value_HMI_AIT301': 0.9995841995841996, 'last_value_HMI_AIT302': 0.9995841995841996, 'last_value_HMI_AIT303': 0.9995841995841996, 'last_value_HMI_AIT401': 0.9995841995841996, 'last_value_HMI_AIT402': 0.9995148995148995, 'last_value_HMI_AIT501': 0.9995841995841996, 'last_value_HMI_AIT502': 0.9995841995841996, 'last_value_HMI_AIT503': 0.9995841995841996, 'last_value_HMI_AIT504': 0.9995841995841996, 'last_value_HMI_DPIT301': 0.9898821898821899, 'last_value_HMI_FIT101': 0.9995841995841996, 'last_value_HMI_FIT102': 0.9995841995841996, 'last_value_HMI_FIT201': 0.9905751905751906, 'last_value_HMI_FIT301': 0.9995841995841996, 'last_value_HMI_FIT401': 0.9995841995841996, 'last_value_HMI_FIT501': 0.9995841995841996, 'last_value_HMI_FIT502': 0.9995841995841996, 'last_value_HMI_FIT503': 0.9995841995841996, 'last_value_HMI_FIT504': 0.9995841995841996, 'last_value_HMI_FIT601': 0.9995841995841996, 'last_value_HMI_FIT602': 0.9995841995841996, 'last_value_HMI_LIT101': 0.9894317394317395, 'last_value_HMI_LIT301': 0.9995841995841996, 'last_value_HMI_LIT401': 0.9995841995841996, 'last_value_HMI_LIT601': 0.9893624393624394, 'last_value_HMI_LIT602': 0.9995841995841996, 'last_value_HMI_MV101': 0.9892931392931393, 'last_value_HMI_MV201': 0.9802841302841303, 'last_value_HMI_MV301': 0.9995841995841996, 'last_value_HMI_MV302': 0.9897089397089397, 'last_value_HMI_MV303': 0.9898128898128898, 'last_value_HMI_MV304': 0.9995841995841996, 'last_value_HMI_MV501': 0.9807692307692307, 'last_value_HMI_MV502': 0.980907830907831, 'last_value_HMI_MV503': 0.9810464310464311, 'last_value_HMI_MV504': 0.9810464310464311, 'last_value_HMI_P101': 0.9710672210672211, 'last_value_HMI_P102': 0.9801455301455302, 'last_value_HMI_P201': 0.9907484407484407, 'last_value_HMI_P202': 0.9906791406791406, 'last_value_HMI_P203': 0.9907484407484407, 'last_value_HMI_P204': 0.9906098406098406, 'last_value_HMI_P205': 0.9907484407484407, 'last_value_HMI_P206': 0.9907830907830908, 'last_value_HMI_P207': 0.9995841995841996, 'last_value_HMI_P208': 0.9995841995841996, 'last_value_HMI_P2_PERMISSIVE': 1.0, 'last_value_HMI_P301': 0.9995841995841996, 'last_value_HMI_P302': 0.9995841995841996, 'last_value_HMI_P3_PERMISSIVE': 1.0, 'last_value_HMI_P401': 0.9995841995841996, 'last_value_HMI_P402': 0.9995841995841996, 'last_value_HMI_P403': 0.9995841995841996, 'last_value_HMI_P404': 0.9995841995841996, 'last_value_HMI_P4_PERMISSIVE': 1.0, 'last_value_HMI_P501': 0.9995841995841996, 'last_value_HMI_P502': 0.9995841995841996, 'last_value_HMI_P5_PERMISSIVE': 1.0, 'last_value_HMI_P5_STATE': 1.0, 'last_value_HMI_P601': 0.9995841995841996, 'last_value_HMI_P602': 0.9995841995841996, 'last_value_HMI_P603': 0.9995841995841996, 'last_value_HMI_P6_PERMISSIVE': 1.0, 'last_value_HMI_PIT501': 0.9995841995841996, 'last_value_HMI_PIT502': 0.9995841995841996, 'last_value_HMI_PIT503': 0.9995841995841996, 'last_value_HMI_P_NAOCL_UF_DUTY': 1.0, 'last_value_HMI_P_RO_FEED_DUTY': 1.0, 'last_value_HMI_UV401': 0.9995841995841996}`
- After (cols with NA): `{}`

