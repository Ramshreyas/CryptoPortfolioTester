{
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "provenance": [],
      "authorship_tag": "ABX9TyOgpSwRH7649QtU3j+UgBPt"
    },
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "language_info": {
      "name": "python"
    }
  },
  "cells": [
    {
      "cell_type": "markdown",
      "source": [
        "# 15 Min Trend Prediction\n",
        "\n",
        "---\n",
        "\n",
        "## Imports"
      ],
      "metadata": {
        "id": "0_h8R9CZjj6q"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "#!pip install --force-reinstall -v \"pandas==1.5.2\""
      ],
      "metadata": {
        "id": "PsevYxLLixvx"
      },
      "execution_count": null,
      "outputs": []
    },
    {
      "cell_type": "code",
      "source": [
        "# Data libraries\n",
        "import numpy as np\n",
        "import pandas as pd\n",
        "from distfit import distfit\n",
        "from datetime import datetime, timedelta\n",
        "import matplotlib.pyplot as plt\n",
        "from matplotlib import rcParams\n",
        "import seaborn as sns\n",
        "import random\n",
        "import scipy.stats as st\n",
        "\n",
        "# Utils\n",
        "import warnings\n",
        "warnings.filterwarnings('ignore')\n",
        "\n",
        "# scikit-learn modules\n",
        "from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelBinarizer\n",
        "from sklearn.model_selection import train_test_split\n",
        "from sklearn.pipeline import Pipeline\n",
        "\n",
        "# Regressor\n",
        "from sklearn.linear_model import LinearRegression, Lasso, Ridge, ElasticNet\n",
        "\n",
        "# Metrics\n",
        "from sklearn.metrics import mean_squared_error, r2_score\n",
        "\n",
        "# Custom utils\n",
        "from regression import Regression"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "SQZSSiBt6wMa",
        "outputId": "aefe52a8-82f2-4c3d-9800-8d3115cbe6b9"
      },
      "execution_count": 1,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stderr",
          "text": [
            "/usr/local/lib/python3.8/dist-packages/scipy/__init__.py:146: UserWarning: A NumPy version >=1.16.5 and <1.23.0 is required for this version of SciPy (detected version 1.24.1\n",
            "  warnings.warn(f\"A NumPy version >={np_minversion} and <{np_maxversion}\"\n"
          ]
        }
      ]
    },
    {
      "cell_type": "markdown",
      "source": [
        "---\n",
        "\n",
        "## Fetch Data"
      ],
      "metadata": {
        "id": "w_D2v16JjppK"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "d = pd.read_pickle('./binance-eth-usdt-spot-1m-2019-2023.pkl')\n",
        "d.index = pd.to_datetime(d.index)"
      ],
      "metadata": {
        "id": "gMdmPLWHi78a"
      },
      "execution_count": 2,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "---\n",
        "\n",
        "## Feature Engineering\n",
        "\n",
        "### 1st Draft\n",
        "\n",
        "- MA 5, 15, 30, 60\n",
        "- VWAP\n",
        "- Dominant Trading Region US, London, Asia"
      ],
      "metadata": {
        "id": "KgUqOkPij1Mx"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "data = d.copy()\n",
        "\n",
        "# Add momentum features\n",
        "data['c-o'] = data['close'] - data['open']\n",
        "data['h-l'] = data['high'] - data['low']\n",
        "\n",
        "# Convert OHLC into returns\n",
        "data['open returns'] = data['open'].pct_change()\n",
        "data['high returns'] = data['high'].pct_change()\n",
        "data['open returns'] = data['low'].pct_change()\n",
        "data['close returns'] = data['close'].pct_change()\n",
        "data['vwap returns'] = data['vwap'].pct_change()\n",
        "\n",
        "# Moving averages of 1 min returns\n",
        "data['MA5'] = data['close returns'].rolling(5).mean()\n",
        "data['MA15'] = data['close returns'].rolling(15).mean()\n",
        "data['MA30'] = data['close returns'].rolling(30).mean()\n",
        "data['MA60'] = data['close returns'].rolling(60).mean()\n",
        "\n",
        "# 5, 15, 30, 60 min returns (not MA)\n",
        "data['5 min returns'] = data.close/data.shift(5).close - 1\n",
        "data['15 min returns'] = data.close/data.shift(15).close - 1\n",
        "data['30 min returns'] = data.close/data.shift(30).close - 1\n",
        "data['60 min returns'] = data.close/data.shift(60).close - 1\n",
        "\n",
        "# Volume by number of trades\n",
        "data['VolCount'] = data['volume']/data['count']\n",
        "\n",
        "# Weekday vs weekend feature\n",
        "data['day'] = data.index.dayofweek\n",
        "data['weekend'] = 0\n",
        "data.loc[data['day'] > 4, 'weekend'] = 1\n",
        "\n",
        "# Dominant trading region\n",
        "data['London'] = 0\n",
        "data['Asia'] = 0\n",
        "data['London'].iloc[data.index.indexer_between_time('07:00:00', '13:30:00', include_start=True)] = 1\n",
        "data['Asia'].iloc[data.index.indexer_between_time('21:00:00', '23:59:00', include_start=True)] = 1\n",
        "data['Asia'].iloc[data.index.indexer_between_time('00:00:00', '07:00:00', include_start=True)] = 1\n",
        "\n",
        "# Target is 15 min ahead returns\n",
        "data['target'] = data.shift(-15).close/data.close - 1\n",
        "data = data.dropna()\n",
        "\n",
        "# Drop unwanted columns\n",
        "data.drop(['open', 'high', 'low', 'close', 'day'], axis=1, inplace=True)    # We don't need the day number\n",
        "\n",
        "data.head()"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 249
        },
        "id": "Nvz8jFMlkCnj",
        "outputId": "30c685d0-75fe-48da-8fa5-3df53ebcd057"
      },
      "execution_count": 4,
      "outputs": [
        {
          "output_type": "execute_result",
          "data": {
            "text/plain": [
              "                                 vwap     volume     usd_volume  count   c-o  \\\n",
              "time                                                                           \n",
              "2019-01-01 01:00:00+00:00  131.828422   60.37882    7919.286031     41 -0.04   \n",
              "2019-01-01 01:01:00+00:00  131.793490   65.41781    8580.199960     42  0.05   \n",
              "2019-01-01 01:02:00+00:00  131.479159  987.39530  129506.767548    251 -0.32   \n",
              "2019-01-01 01:03:00+00:00  131.580908  269.58764   35356.418986     99  0.10   \n",
              "2019-01-01 01:04:00+00:00  131.558398   48.55283    6367.703655     24  0.00   \n",
              "\n",
              "                            h-l  open returns  high returns  close returns  \\\n",
              "time                                                                         \n",
              "2019-01-01 01:00:00+00:00  0.13      0.001064      0.000455      -0.000228   \n",
              "2019-01-01 01:01:00+00:00  0.05      0.000152     -0.000455       0.000228   \n",
              "2019-01-01 01:02:00+00:00  0.61     -0.003870      0.000379      -0.002428   \n",
              "2019-01-01 01:03:00+00:00  0.14      0.001752     -0.001820       0.000684   \n",
              "2019-01-01 01:04:00+00:00  0.07      0.000152     -0.000380      -0.000228   \n",
              "\n",
              "                           vwap returns  ...      MA60  5 min returns  \\\n",
              "time                                     ...                            \n",
              "2019-01-01 01:00:00+00:00      0.000646  ...  0.000043      -0.001061   \n",
              "2019-01-01 01:01:00+00:00     -0.000265  ...  0.000076      -0.000834   \n",
              "2019-01-01 01:02:00+00:00     -0.002385  ...  0.000033      -0.003335   \n",
              "2019-01-01 01:03:00+00:00      0.000774  ...  0.000040      -0.000608   \n",
              "2019-01-01 01:04:00+00:00     -0.000171  ...  0.000037      -0.001972   \n",
              "\n",
              "                           15 min returns  30 min returns  60 min returns  \\\n",
              "time                                                                        \n",
              "2019-01-01 01:00:00+00:00        0.000380        0.003655        0.002587   \n",
              "2019-01-01 01:01:00+00:00        0.000000        0.003578        0.004572   \n",
              "2019-01-01 01:02:00+00:00       -0.002806       -0.000456        0.001981   \n",
              "2019-01-01 01:03:00+00:00       -0.003936        0.000076        0.002361   \n",
              "2019-01-01 01:04:00+00:00       -0.003484        0.000000        0.002209   \n",
              "\n",
              "                           VolCount  weekend  London  Asia    target  \n",
              "time                                                                  \n",
              "2019-01-01 01:00:00+00:00  1.472654        0       0     1 -0.001745  \n",
              "2019-01-01 01:01:00+00:00  1.557567        0       0     1 -0.002124  \n",
              "2019-01-01 01:02:00+00:00  3.933846        0       0     1  0.000304  \n",
              "2019-01-01 01:03:00+00:00  2.723107        0       0     1  0.000456  \n",
              "2019-01-01 01:04:00+00:00  2.023035        0       0     1 -0.000152  \n",
              "\n",
              "[5 rows x 23 columns]"
            ],
            "text/html": [
              "\n",
              "  <div id=\"df-2eed7bed-2a1d-4014-9f93-47331e855454\">\n",
              "    <div class=\"colab-df-container\">\n",
              "      <div>\n",
              "<style scoped>\n",
              "    .dataframe tbody tr th:only-of-type {\n",
              "        vertical-align: middle;\n",
              "    }\n",
              "\n",
              "    .dataframe tbody tr th {\n",
              "        vertical-align: top;\n",
              "    }\n",
              "\n",
              "    .dataframe thead th {\n",
              "        text-align: right;\n",
              "    }\n",
              "</style>\n",
              "<table border=\"1\" class=\"dataframe\">\n",
              "  <thead>\n",
              "    <tr style=\"text-align: right;\">\n",
              "      <th></th>\n",
              "      <th>vwap</th>\n",
              "      <th>volume</th>\n",
              "      <th>usd_volume</th>\n",
              "      <th>count</th>\n",
              "      <th>c-o</th>\n",
              "      <th>h-l</th>\n",
              "      <th>open returns</th>\n",
              "      <th>high returns</th>\n",
              "      <th>close returns</th>\n",
              "      <th>vwap returns</th>\n",
              "      <th>...</th>\n",
              "      <th>MA60</th>\n",
              "      <th>5 min returns</th>\n",
              "      <th>15 min returns</th>\n",
              "      <th>30 min returns</th>\n",
              "      <th>60 min returns</th>\n",
              "      <th>VolCount</th>\n",
              "      <th>weekend</th>\n",
              "      <th>London</th>\n",
              "      <th>Asia</th>\n",
              "      <th>target</th>\n",
              "    </tr>\n",
              "    <tr>\n",
              "      <th>time</th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "      <th></th>\n",
              "    </tr>\n",
              "  </thead>\n",
              "  <tbody>\n",
              "    <tr>\n",
              "      <th>2019-01-01 01:00:00+00:00</th>\n",
              "      <td>131.828422</td>\n",
              "      <td>60.37882</td>\n",
              "      <td>7919.286031</td>\n",
              "      <td>41</td>\n",
              "      <td>-0.04</td>\n",
              "      <td>0.13</td>\n",
              "      <td>0.001064</td>\n",
              "      <td>0.000455</td>\n",
              "      <td>-0.000228</td>\n",
              "      <td>0.000646</td>\n",
              "      <td>...</td>\n",
              "      <td>0.000043</td>\n",
              "      <td>-0.001061</td>\n",
              "      <td>0.000380</td>\n",
              "      <td>0.003655</td>\n",
              "      <td>0.002587</td>\n",
              "      <td>1.472654</td>\n",
              "      <td>0</td>\n",
              "      <td>0</td>\n",
              "      <td>1</td>\n",
              "      <td>-0.001745</td>\n",
              "    </tr>\n",
              "    <tr>\n",
              "      <th>2019-01-01 01:01:00+00:00</th>\n",
              "      <td>131.793490</td>\n",
              "      <td>65.41781</td>\n",
              "      <td>8580.199960</td>\n",
              "      <td>42</td>\n",
              "      <td>0.05</td>\n",
              "      <td>0.05</td>\n",
              "      <td>0.000152</td>\n",
              "      <td>-0.000455</td>\n",
              "      <td>0.000228</td>\n",
              "      <td>-0.000265</td>\n",
              "      <td>...</td>\n",
              "      <td>0.000076</td>\n",
              "      <td>-0.000834</td>\n",
              "      <td>0.000000</td>\n",
              "      <td>0.003578</td>\n",
              "      <td>0.004572</td>\n",
              "      <td>1.557567</td>\n",
              "      <td>0</td>\n",
              "      <td>0</td>\n",
              "      <td>1</td>\n",
              "      <td>-0.002124</td>\n",
              "    </tr>\n",
              "    <tr>\n",
              "      <th>2019-01-01 01:02:00+00:00</th>\n",
              "      <td>131.479159</td>\n",
              "      <td>987.39530</td>\n",
              "      <td>129506.767548</td>\n",
              "      <td>251</td>\n",
              "      <td>-0.32</td>\n",
              "      <td>0.61</td>\n",
              "      <td>-0.003870</td>\n",
              "      <td>0.000379</td>\n",
              "      <td>-0.002428</td>\n",
              "      <td>-0.002385</td>\n",
              "      <td>...</td>\n",
              "      <td>0.000033</td>\n",
              "      <td>-0.003335</td>\n",
              "      <td>-0.002806</td>\n",
              "      <td>-0.000456</td>\n",
              "      <td>0.001981</td>\n",
              "      <td>3.933846</td>\n",
              "      <td>0</td>\n",
              "      <td>0</td>\n",
              "      <td>1</td>\n",
              "      <td>0.000304</td>\n",
              "    </tr>\n",
              "    <tr>\n",
              "      <th>2019-01-01 01:03:00+00:00</th>\n",
              "      <td>131.580908</td>\n",
              "      <td>269.58764</td>\n",
              "      <td>35356.418986</td>\n",
              "      <td>99</td>\n",
              "      <td>0.10</td>\n",
              "      <td>0.14</td>\n",
              "      <td>0.001752</td>\n",
              "      <td>-0.001820</td>\n",
              "      <td>0.000684</td>\n",
              "      <td>0.000774</td>\n",
              "      <td>...</td>\n",
              "      <td>0.000040</td>\n",
              "      <td>-0.000608</td>\n",
              "      <td>-0.003936</td>\n",
              "      <td>0.000076</td>\n",
              "      <td>0.002361</td>\n",
              "      <td>2.723107</td>\n",
              "      <td>0</td>\n",
              "      <td>0</td>\n",
              "      <td>1</td>\n",
              "      <td>0.000456</td>\n",
              "    </tr>\n",
              "    <tr>\n",
              "      <th>2019-01-01 01:04:00+00:00</th>\n",
              "      <td>131.558398</td>\n",
              "      <td>48.55283</td>\n",
              "      <td>6367.703655</td>\n",
              "      <td>24</td>\n",
              "      <td>0.00</td>\n",
              "      <td>0.07</td>\n",
              "      <td>0.000152</td>\n",
              "      <td>-0.000380</td>\n",
              "      <td>-0.000228</td>\n",
              "      <td>-0.000171</td>\n",
              "      <td>...</td>\n",
              "      <td>0.000037</td>\n",
              "      <td>-0.001972</td>\n",
              "      <td>-0.003484</td>\n",
              "      <td>0.000000</td>\n",
              "      <td>0.002209</td>\n",
              "      <td>2.023035</td>\n",
              "      <td>0</td>\n",
              "      <td>0</td>\n",
              "      <td>1</td>\n",
              "      <td>-0.000152</td>\n",
              "    </tr>\n",
              "  </tbody>\n",
              "</table>\n",
              "<p>5 rows × 23 columns</p>\n",
              "</div>\n",
              "      <button class=\"colab-df-convert\" onclick=\"convertToInteractive('df-2eed7bed-2a1d-4014-9f93-47331e855454')\"\n",
              "              title=\"Convert this dataframe to an interactive table.\"\n",
              "              style=\"display:none;\">\n",
              "        \n",
              "  <svg xmlns=\"http://www.w3.org/2000/svg\" height=\"24px\"viewBox=\"0 0 24 24\"\n",
              "       width=\"24px\">\n",
              "    <path d=\"M0 0h24v24H0V0z\" fill=\"none\"/>\n",
              "    <path d=\"M18.56 5.44l.94 2.06.94-2.06 2.06-.94-2.06-.94-.94-2.06-.94 2.06-2.06.94zm-11 1L8.5 8.5l.94-2.06 2.06-.94-2.06-.94L8.5 2.5l-.94 2.06-2.06.94zm10 10l.94 2.06.94-2.06 2.06-.94-2.06-.94-.94-2.06-.94 2.06-2.06.94z\"/><path d=\"M17.41 7.96l-1.37-1.37c-.4-.4-.92-.59-1.43-.59-.52 0-1.04.2-1.43.59L10.3 9.45l-7.72 7.72c-.78.78-.78 2.05 0 2.83L4 21.41c.39.39.9.59 1.41.59.51 0 1.02-.2 1.41-.59l7.78-7.78 2.81-2.81c.8-.78.8-2.07 0-2.86zM5.41 20L4 18.59l7.72-7.72 1.47 1.35L5.41 20z\"/>\n",
              "  </svg>\n",
              "      </button>\n",
              "      \n",
              "  <style>\n",
              "    .colab-df-container {\n",
              "      display:flex;\n",
              "      flex-wrap:wrap;\n",
              "      gap: 12px;\n",
              "    }\n",
              "\n",
              "    .colab-df-convert {\n",
              "      background-color: #E8F0FE;\n",
              "      border: none;\n",
              "      border-radius: 50%;\n",
              "      cursor: pointer;\n",
              "      display: none;\n",
              "      fill: #1967D2;\n",
              "      height: 32px;\n",
              "      padding: 0 0 0 0;\n",
              "      width: 32px;\n",
              "    }\n",
              "\n",
              "    .colab-df-convert:hover {\n",
              "      background-color: #E2EBFA;\n",
              "      box-shadow: 0px 1px 2px rgba(60, 64, 67, 0.3), 0px 1px 3px 1px rgba(60, 64, 67, 0.15);\n",
              "      fill: #174EA6;\n",
              "    }\n",
              "\n",
              "    [theme=dark] .colab-df-convert {\n",
              "      background-color: #3B4455;\n",
              "      fill: #D2E3FC;\n",
              "    }\n",
              "\n",
              "    [theme=dark] .colab-df-convert:hover {\n",
              "      background-color: #434B5C;\n",
              "      box-shadow: 0px 1px 3px 1px rgba(0, 0, 0, 0.15);\n",
              "      filter: drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.3));\n",
              "      fill: #FFFFFF;\n",
              "    }\n",
              "  </style>\n",
              "\n",
              "      <script>\n",
              "        const buttonEl =\n",
              "          document.querySelector('#df-2eed7bed-2a1d-4014-9f93-47331e855454 button.colab-df-convert');\n",
              "        buttonEl.style.display =\n",
              "          google.colab.kernel.accessAllowed ? 'block' : 'none';\n",
              "\n",
              "        async function convertToInteractive(key) {\n",
              "          const element = document.querySelector('#df-2eed7bed-2a1d-4014-9f93-47331e855454');\n",
              "          const dataTable =\n",
              "            await google.colab.kernel.invokeFunction('convertToInteractive',\n",
              "                                                     [key], {});\n",
              "          if (!dataTable) return;\n",
              "\n",
              "          const docLinkHtml = 'Like what you see? Visit the ' +\n",
              "            '<a target=\"_blank\" href=https://colab.research.google.com/notebooks/data_table.ipynb>data table notebook</a>'\n",
              "            + ' to learn more about interactive tables.';\n",
              "          element.innerHTML = '';\n",
              "          dataTable['output_type'] = 'display_data';\n",
              "          await google.colab.output.renderOutput(dataTable, element);\n",
              "          const docLink = document.createElement('div');\n",
              "          docLink.innerHTML = docLinkHtml;\n",
              "          element.appendChild(docLink);\n",
              "        }\n",
              "      </script>\n",
              "    </div>\n",
              "  </div>\n",
              "  "
            ]
          },
          "metadata": {},
          "execution_count": 4
        },
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "Warning: Total number of columns (23) exceeds max_columns (20) limiting to first (20) columns.\n"
          ]
        }
      ]
    },
    {
      "cell_type": "code",
      "source": [],
      "metadata": {
        "id": "-5tt2XlA8J0Z"
      },
      "execution_count": null,
      "outputs": []
    }
  ]
}