# AxieOS System Architecture

```
                           +----------------------+
                           |      Account         |
                           +----------------------+
                                      |
                                      |
                           owns one or more
                                      |
                                      ▼
                           +----------------------+
                           |       Player         |
                           +----------------------+
                                      |
              +-----------------------+-----------------------+
              |                       |                       |
              ▼                       ▼                       ▼
      +---------------+       +---------------+      +----------------+
      |   Wallet(s)   |       |    Assets     |      |   Strategies   |
      +---------------+       +---------------+      +----------------+
              |                       |
              |                       |
              |               +-------+-------+
              |               |               |
              ▼               ▼               ▼
       Transactions        Axies         Land Plots
                                |
                                |
                                ▼
                         +---------------+
                         | Delegations   |
                         +---------------+
                                |
                                ▼
                          Scholar Wallet

------------------------------------------------------------

Analytics Layer

- Wallet Analytics
- Bounty Analytics
- Terrarium Analytics
- ROI Analytics

------------------------------------------------------------

Decision Layer

- Strategy Lab
- Optimization
- Probability Engine
- Machine Learning

------------------------------------------------------------

Presentation Layer

- Google Sheets
- Python Dashboard
- Reports
- GitHub Documentation
```
