# AI-TDP Project Bibliography

**Compiled:** 2026-07-16  
**Purpose:** Ready-to-paste references for reports, theses, and presentations covering the three datasets used in this project (SWaT, ELEGANT, IEC 60870-5-104).

---

## How to cite (quick guide)

| You use… | Cite primarily |
| :--- | :--- |
| SWaT testbed / classic labeled benchmark | [1], [2] |
| SWaT.A12 (2026 OT historian CSV, local) | [1], [3] |
| ELEGANT PCAPs / extracted flow CSVs | [4], [7]; project context [5] |
| IEC-104 balanced or attack-package CSVs | [8], [10]; methodology [9] |
| CICFlowMeter 84-column flow features | [12] |
| OpenPLC stack (ELEGANT testbed) | [6] |

---

## Primary references (numbered)

### SWaT — Secure Water Treatment

**[1] SWaT testbed (architecture & research goals)**

- **IEEE:** A. P. Mathur and N. O. Tippenhauer, "SWaT: a water treatment testbed for research and training on ICS security," in *Proc. Int. Workshop Cyber-physical Syst. Smart Water Networks (CySWater)*, 2016, pp. 1–6. doi: [10.1109/CySWater.2016.7469060](https://doi.org/10.1109/CySWater.2016.7469060)

- **APA:** Mathur, A. P., & Tippenhauer, N. O. (2016). SWaT: A water treatment testbed for research and training on ICS security. In *Proceedings of the International Workshop on Cyber-physical Systems for Smart Water Networks (CySWater)* (pp. 1–6). IEEE. https://doi.org/10.1109/CySWater.2016.7469060

---

**[2] Classic labeled SWaT dataset (Dec 2015 benchmark)**

- **IEEE:** J. Goh, S. Adepu, K. N. Junejo, and A. P. Mathur, "A dataset to support research in the design of secure water treatment systems," in *Critical Information Infrastructures Security: CRITIS 2016*, ser. LNCS, vol. 10242, G. M. Havârneanu et al., Eds. Springer, 2017, pp. 88–99. doi: [10.1007/978-3-319-71368-7_8](https://doi.org/10.1007/978-3-319-71368-7_8)

- **APA:** Goh, J., Adepu, S., Junejo, K. N., & Mathur, A. P. (2017). A dataset to support research in the design of secure water treatment systems. In G. M. Havârneanu, R. Setola, H. Nassopoulos, & S. D. Wolthusen (Eds.), *Critical information infrastructures security* (LNCS 10242, pp. 88–99). Springer. https://doi.org/10.1007/978-3-319-71368-7_8

---

**[3] SWaT official dataset portal (iTrust — includes A12 and newer exports)**

- **Web:** iTrust Centre for Research in Cyber Security, Singapore University of Technology and Design. *Secure Water Treatment (SWaT) — dataset characteristics.* Retrieved from [https://www.sutd.edu.sg/itrust/itrust-labs/datasets/dataset-characteristics/swat/](https://www.sutd.edu.sg/itrust/itrust-labs/datasets/dataset-characteristics/swat/)

- **APA:** iTrust Centre for Research in Cyber Security. (n.d.). *Secure Water Treatment (SWaT) — dataset characteristics.* Singapore University of Technology and Design. Retrieved July 16, 2026, from https://www.sutd.edu.sg/itrust/itrust-labs/datasets/dataset-characteristics/swat/

> **Local note:** This project uses `SWaT.A12_OTDataset_Mar_26` (87 OT historian columns, no attack label). Papers [1]–[2] describe the testbed and the classic labeled export; [3] is the authoritative source for newer historian releases.

---

### ELEGANT — PLC DoS / MiTM

**[4] ELEGANT dataset paper (direct PCAP documentation)**

- **IEEE/arXiv:** B. Sousa, T. Cruz, M. Arieiro, and V. Pereira, "An ELEGANT dataset with Denial of Service and Man in The Middle attacks," arXiv:2103.09380, 2021. [https://arxiv.org/abs/2103.09380](https://arxiv.org/abs/2103.09380)

- **APA:** Sousa, B., Cruz, T., Arieiro, M., & Pereira, V. (2021). *An ELEGANT dataset with Denial of Service and Man in The Middle attacks* (arXiv:2103.09380). arXiv. https://arxiv.org/abs/2103.09380

---

**[5] ELEGANT project (digital twins & Fed4Fire+ context)**

- **IEEE:** B. Sousa, M. Arieiro, V. Pereira, J. Correia, N. Lourenço, and T. Cruz, "ELEGANT: Security of critical infrastructures with digital twins," *IEEE Access*, vol. 9, pp. 107574–107588, 2021. doi: [10.1109/ACCESS.2021.3100708](https://doi.org/10.1109/ACCESS.2021.3100708)

- **APA:** Sousa, B., Arieiro, M., Pereira, V., Correia, J., Lourenço, N., & Cruz, T. (2021). ELEGANT: Security of critical infrastructures with digital twins. *IEEE Access*, *9*, 107574–107588. https://doi.org/10.1109/ACCESS.2021.3100708

---

**[6] OpenPLC (PLC software used in ELEGANT testbed)**

- **IEEE:** T. R. Alves, M. Buratto, F. M. de Souza, and T. V. Rodrigues, "OpenPLC: An open source alternative to automation," in *Proc. IEEE Global Humanitarian Technol. Conf. (GHTC)*, 2014, pp. 585–589. doi: [10.1109/GHTC.2014.6970342](https://doi.org/10.1109/GHTC.2014.6970342)

- **APA:** Alves, T. R., Buratto, M., de Souza, F. M., & Rodrigues, T. V. (2014). OpenPLC: An open source alternative to automation. In *2014 IEEE Global Humanitarian Technology Conference (GHTC)* (pp. 585–589). IEEE. https://doi.org/10.1109/GHTC.2014.6970342

---

**[7] ELEGANT dataset record (IEEE DataPort)**

- **Dataset:** B. Sousa et al., "Denial of Service and Man-in-the-Middle Attacks on Programmable Logic Controllers," IEEE DataPort, 2021. doi: [10.21227/mewp-g646](https://doi.org/10.21227/mewp-g646)

- **APA:** Sousa, B., Cruz, T., Arieiro, M., & Pereira, V. (2021). *Denial of Service and Man-in-the-Middle Attacks on Programmable Logic Controllers* [Data set]. IEEE DataPort. https://doi.org/10.21227/mewp-g646

---

### IEC 60870-5-104 Intrusion Detection Dataset

**[8] Primary paper (required when using IEC-104 dataset)**

- **IEEE:** P. Radoglou-Grammatikis, K. Rompolos, P. Sarigiannidis, V. Argyriou, T. Lagkas, A. Sarigiannidis, S. Goudos, and S. Wan, "Modeling, detecting, and mitigating threats against industrial healthcare systems: A combined software defined networking and reinforcement learning approach," *IEEE Trans. Ind. Informat.*, vol. 18, no. 3, pp. 2041–2052, Mar. 2022. doi: [10.1109/TII.2021.3093905](https://doi.org/10.1109/TII.2021.3093905)

- **APA:** Radoglou-Grammatikis, P., Rompolos, K., Sarigiannidis, P., Argyriou, V., Lagkas, T., Sarigiannidis, A., Goudos, S., & Wan, S. (2022). Modeling, detecting, and mitigating threats against industrial healthcare systems: A combined software defined networking and reinforcement learning approach. *IEEE Transactions on Industrial Informatics*, *18*(3), 2041–2052. https://doi.org/10.1109/TII.2021.3093905

---

**[9] IDS dataset evaluation framework (IEC-104 built to this methodology)**

- **IEEE:** A. Gharib, I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, "An evaluation framework for intrusion detection dataset," in *Proc. Int. Conf. Inf. Sci. Security (ICISS)*, 2016, pp. 1–6. doi: [10.1109/ICISSEC.2016.7885840](https://doi.org/10.1109/ICISSEC.2016.7885840)

- **APA:** Gharib, A., Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2016). An evaluation framework for intrusion detection dataset. In *2016 International Conference on Information Science and Security (ICISS)* (pp. 1–6). IEEE. https://doi.org/10.1109/ICISSEC.2016.7885840

---

**[10] IEC-104 dataset record (Zenodo — primary download)**

- **Dataset:** P. Radoglou-Grammatikis et al., "IEC 60870-5-104 Intrusion Detection Dataset," Zenodo, Sep. 2022. [https://zenodo.org/records/7108614](https://zenodo.org/records/7108614)

- **APA:** Radoglou-Grammatikis, P., Lagkas, T., Argyriou, V., & Sarigiannidis, P. (2022). *IEC 60870-5-104 Intrusion Detection Dataset* [Data set]. Zenodo. https://zenodo.org/records/7108614

---

**[11] IEC-104 dataset mirror (IEEE DataPort)**

- **Dataset:** P. Radoglou-Grammatikis et al., "IEC 60870-5-104 Intrusion Detection Dataset," IEEE DataPort. doi: [10.21227/fj7s-f281](https://doi.org/10.21227/fj7s-f281)

- **APA:** Radoglou-Grammatikis, P., Lagkas, T., Argyriou, V., & Sarigiannidis, P. (2022). *IEC 60870-5-104 Intrusion Detection Dataset* [Data set]. IEEE DataPort. https://doi.org/10.21227/fj7s-f281

> **Funding (from dataset ReadMe):** European Union H2020 **ELECTRON** (101021936) and **SDN-microSENSE** (833955).

---

### Cross-cutting — feature extraction & flow analysis

**[12] CICFlowMeter / flow feature methodology**

- **IEEE:** I. Sharafaldin, A. Habibi Lashkari, and A. A. Ghorbani, "Toward generating a new intrusion detection dataset and intrusion traffic characterization," in *Proc. 4th Int. Conf. Inf. Syst. Security Privacy (ICISSP)*, 2018, pp. 108–116. doi: [10.5220/0006639801080116](https://doi.org/10.5220/0006639801080116)

- **APA:** Sharafaldin, I., Lashkari, A., & Ghorbani, A. (2018). Toward generating a new intrusion detection dataset and intrusion traffic characterization. In *Proceedings of the 4th International Conference on Information Systems Security and Privacy (ICISSP)* (pp. 108–116). SCITEPRESS. https://doi.org/10.5220/0006639801080116

---

## Supporting references (cited in ELEGANT dataset paper [4])

**[13]** A. Huseinovic, S. Mrdovic, K. Bicakci, and S. Uludag, "A survey of denial-of-service attacks and solutions in the smart grid," *IEEE Access*, vol. 8, pp. 177447–177470, 2020. doi: [10.1109/ACCESS.2020.3019699](https://doi.org/10.1109/ACCESS.2020.3019699)

**[14]** C. Foglietta, D. Masucci, C. Palazzo, R. Santini, S. Panzieri, L. Rosa, T. Cruz, and L. Lev, "From detecting cyber-attacks to mitigating risk within a hybrid environment," *IEEE Syst. J.*, vol. 13, no. 1, pp. 424–435, 2019. doi: [10.1109/JSYST.2018.2838283](https://doi.org/10.1109/JSYST.2018.2838283)

**[15]** L. Rosa, T. Cruz, P. Simões, E. Monteiro, and L. Lev, "Attacking SCADA systems: A practical perspective," in *Proc. IFIP/IEEE Symp. Integr. Netw. Service Manage. (IM)*, 2017, pp. 741–746. doi: [10.23919/INM.2017.7987333](https://doi.org/10.23919/INM.2017.7987333)

**[16]** M. Niedermaier, F. Fischer, D. Merli, and G. Sigl, "Network scanning and mapping for IIoT edge node device security," in *Proc. Int. Conf. Appl. Electron. (AE)*, 2019, pp. 1–6. doi: [10.1109/AE.2019.8864563](https://doi.org/10.1109/AE.2019.8864563)

---

## Copy-paste reference list (IEEE, condensed)

```
[1]  A. P. Mathur and N. O. Tippenhauer, "SWaT: a water treatment testbed for research and training on ICS security," in Proc. CySWater, 2016. doi: 10.1109/CySWater.2016.7469060
[2]  J. Goh et al., "A dataset to support research in the design of secure water treatment systems," in CRITIS 2016, LNCS 10242, 2017. doi: 10.1007/978-3-319-71368-7_8
[3]  iTrust, "Secure Water Treatment (SWaT) — dataset characteristics," SUTD. https://www.sutd.edu.sg/itrust/itrust-labs/datasets/dataset-characteristics/swat/
[4]  B. Sousa et al., "An ELEGANT dataset with Denial of Service and Man in The Middle attacks," arXiv:2103.09380, 2021.
[5]  B. Sousa et al., "ELEGANT: Security of critical infrastructures with digital twins," IEEE Access, vol. 9, 2021. doi: 10.1109/ACCESS.2021.3100708
[6]  T. R. Alves et al., "OpenPLC: An open source alternative to automation," in Proc. GHTC, 2014. doi: 10.1109/GHTC.2014.6970342
[7]  B. Sousa et al., "Denial of Service and Man-in-the-Middle Attacks on Programmable Logic Controllers," IEEE DataPort, 2021. doi: 10.21227/mewp-g646
[8]  P. Radoglou-Grammatikis et al., "Modeling, detecting, and mitigating threats against industrial healthcare systems," IEEE Trans. Ind. Informat., vol. 18, no. 3, 2022. doi: 10.1109/TII.2021.3093905
[9]  A. Gharib et al., "An evaluation framework for intrusion detection dataset," in Proc. ICISS, 2016. doi: 10.1109/ICISSEC.2016.7885840
[10] P. Radoglou-Grammatikis et al., "IEC 60870-5-104 Intrusion Detection Dataset," Zenodo, 2022. https://zenodo.org/records/7108614
[11] P. Radoglou-Grammatikis et al., "IEC 60870-5-104 Intrusion Detection Dataset," IEEE DataPort. doi: 10.21227/fj7s-f281
[12] I. Sharafaldin et al., "Toward generating a new intrusion detection dataset and intrusion traffic characterization," in Proc. ICISSP, 2018. doi: 10.5220/0006639801080116
```

---

## Related project documentation (this repo)

| Document | Path |
| :--- | :--- |
| Feature inventory report | `reports/DATASET_FEATURE_REPORT.md` |
| Architecture & devices | `reports/PROFESSIONAL_DATASET_DOCUMENTATION.md` |
| Training explainer | `reports/TRAINING_EXPLAINER.md` |
| Data directory map | `data/README.md` |
| Download status | `data/DOWNLOAD_STATUS.md` |
| Feature inventory (Word) | `reports/Local_Dataset_Feature_Inventory.docx` |

---

## BibTeX (selected entries)

```bibtex
@inproceedings{mathur2016swat,
  author    = {Mathur, Aditya P. and Tippenhauer, Nils Ole},
  title     = {{SWaT}: A Water Treatment Testbed for Research and Training on {ICS} Security},
  booktitle = {Proc. CySWater},
  year      = {2016},
  doi       = {10.1109/CySWater.2016.7469060}
}

@inproceedings{goh2017swatdataset,
  author    = {Goh, Jonathan and Adepu, Sridhar and Junejo, Khurum Nazir and Mathur, Aditya P.},
  title     = {A Dataset to Support Research in the Design of Secure Water Treatment Systems},
  booktitle = {CRITIS},
  series    = {LNCS},
  volume    = {10242},
  pages     = {88--99},
  year      = {2017},
  doi       = {10.1007/978-3-319-71368-7_8}
}

@article{sousa2021elegantarxiv,
  author  = {Sousa, Bruno and Cruz, Tiago and Arieiro, Miguel and Pereira, Vasco},
  title   = {An {ELEGANT} Dataset with Denial of Service and Man in The Middle Attacks},
  journal = {arXiv preprint arXiv:2103.09380},
  year    = {2021}
}

@article{sousa2021elegant,
  author  = {Sousa, Bruno and Arieiro, Miguel and Pereira, Vasco and Correia, Jo{\~a}o and Louren{\c{c}}o, Nuno and Cruz, Tiago},
  title   = {{ELEGANT}: Security of Critical Infrastructures With Digital Twins},
  journal = {IEEE Access},
  volume  = {9},
  pages   = {107574--107588},
  year    = {2021},
  doi     = {10.1109/ACCESS.2021.3100708}
}

@article{radoglou2022iec104,
  author  = {Radoglou-Grammatikis, Panagiotis and Rompolos, Konstantinos and Sarigiannidis, Panagiotis and Argyriou, Vasileios and Lagkas, Thomas and Sarigiannidis, Anastasios and Goudos, Sotirios and Wan, Shen},
  title   = {Modeling, Detecting, and Mitigating Threats Against Industrial Healthcare Systems: A Combined Software Defined Networking and Reinforcement Learning Approach},
  journal = {IEEE Transactions on Industrial Informatics},
  volume  = {18},
  number  = {3},
  pages   = {2041--2052},
  year    = {2022},
  doi     = {10.1109/TII.2021.3093905}
}

@inproceedings{gharib2016framework,
  author    = {Gharib, Amirhossein and Sharafaldin, Iman and Lashkari, Arash Habibi and Ghorbani, Ali A.},
  title     = {An Evaluation Framework for Intrusion Detection Dataset},
  booktitle = {Proc. ICISS},
  pages     = {1--6},
  year      = {2016},
  doi       = {10.1109/ICISSEC.2016.7885840}
}

@inproceedings{sharafaldin2018cicids,
  author    = {Sharafaldin, Iman and Lashkari, Arash Habibi and Ghorbani, Ali A.},
  title     = {Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization},
  booktitle = {Proc. ICISSP},
  pages     = {108--116},
  year      = {2018},
  doi       = {10.5220/0006639801080116}
}

@misc{sousa2021elegantdata,
  author       = {Sousa, Bruno and Cruz, Tiago and Arieiro, Miguel and Pereira, Vasco},
  title        = {Denial of Service and Man-in-the-Middle Attacks on Programmable Logic Controllers},
  year         = {2021},
  publisher    = {IEEE DataPort},
  doi          = {10.21227/mewp-g646}
}

@misc{radoglou2022iec104data,
  author       = {Radoglou-Grammatikis, Panagiotis and others},
  title        = {{IEC} 60870-5-104 Intrusion Detection Dataset},
  year         = {2022},
  publisher    = {Zenodo},
  url          = {https://zenodo.org/records/7108614}
}
```
