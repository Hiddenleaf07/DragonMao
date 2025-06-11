import os
import sys
import warnings
import logging
from time import sleep
warnings.simplefilter("ignore", DeprecationWarning)
warnings.simplefilter("ignore", FutureWarning)
import pandas as pd
import yfinance as yf
from yfinance import shared
from PKDevTools.classes.Utils import USER_AGENTS
import random
from yfinance.data import YfData
from yfinance.exceptions import YFPricesMissingError, YFInvalidPeriodError, YFRateLimitError
from concurrent.futures import ThreadPoolExecutor
from PKDevTools.classes.PKDateUtilities import PKDateUtilities
from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.Fetcher import StockDataEmptyException
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.SuppressOutput import SuppressOutput
from PKNSETools.PKNSEStockDataFetcher import nseStockDataFetcher
from pkscreener.classes.PKTask import PKTask
from PKDevTools.classes.OutputControls import OutputControls



class screenerStockDataFetcher(nseStockDataFetcher):
    _tickersInfoDict={}
    def fetchStockDataWithArgs(self, *args):
        task = None
        if isinstance(args[0], PKTask):
            task = args[0]
            stockCode,period,duration,exchangeSuffix = task.long_running_fn_args
        else:
            stockCode,period,duration,exchangeSuffix = args[0],args[1],args[2],args[3]
        result = self.fetchStockData(stockCode,period,duration,None,0,0,0,exchangeSuffix=exchangeSuffix,printCounter=False)
        if task is not None:
            if task.taskId >= 0:
                task.progressStatusDict[task.taskId] = {'progress': 0, 'total': 1}
                task.resultsDict[task.taskId] = result
                task.progressStatusDict[task.taskId] = {'progress': 1, 'total': 1}
            task.result = result
        return result

    def get_stats(self,ticker):
        info = yf.Tickers(ticker).tickers[ticker].fast_info
        screenerStockDataFetcher._tickersInfoDict[ticker] = {"marketCap":info.market_cap if info is not None else 0}

    def fetchAdditionalTickerInfo(self,ticker_list,exchangeSuffix=".NS"):
        if not isinstance(ticker_list,list):
            raise TypeError("ticker_list must be a list")
        if len(exchangeSuffix) > 0:
            ticker_list = [(f"{x}{exchangeSuffix}" if not x.endswith(exchangeSuffix) else x) for x in ticker_list]
        screenerStockDataFetcher._tickersInfoDict = {}
        with ThreadPoolExecutor() as executor:
            executor.map(self.get_stats, ticker_list)
        return screenerStockDataFetcher._tickersInfoDict

    # Fetch stock price data from Yahoo finance
    def fetchStockData(
        self,
        stockCode,
        period,
        duration,
        proxyServer=None,
        screenResultsCounter=0,
        screenCounter=0,
        totalSymbols=0,
        printCounter=False,
        start=None, 
        end=None,
        exchangeSuffix=".NS",
        attempt = 0
    ):
        if isinstance(stockCode,list):
            if len(exchangeSuffix) > 0:
                stockCode = [(f"{x}{exchangeSuffix}" if (not x.endswith(exchangeSuffix) and not x.startswith("^")) else x) for x in stockCode]
        elif isinstance(stockCode,str):
            if len(exchangeSuffix) > 0:
                stockCode = f"{stockCode}{exchangeSuffix}" if (not stockCode.endswith(exchangeSuffix) and not stockCode.startswith("^")) else stockCode
        if (period in ["1d","5d","1mo","3mo","5mo"] or duration[-1] in ["m","h"]):
           
            start = None
            end = None
    
        data = None
        with SuppressOutput(suppress_stdout=(not printCounter), suppress_stderr=(not printCounter)):
            try:
                data = yf.download(
                    tickers=stockCode,
                    period=period,
                    interval=duration,
                    proxy=proxyServer,
                    progress=False,
                    rounding = True,
                    group_by='ticker',
                    timeout=self.configManager.longTimeout, 
                    start=start,
                    end=end,
                    auto_adjust=True,
                    threads=len(stockCode) if not isinstance(stockCode,str) else True
                )
                if isinstance(stockCode,str):
                    if (data is None or data.empty):
                        for ticker in shared._ERRORS:
                            err = shared._ERRORS.get(ticker)
                            
                            if "YFInvalidPeriodError" in err: #and "Period \'1mo\' is invalid" not in err:
                                recommendedPeriod = period
                                if isinstance(err,YFInvalidPeriodError):
                                    recommendedPeriod = err.valid_ranges[-1]
                                else:
                                    recommendedPeriod = str(err).split("[")[1].split("]")[0].split(",")[-1].strip()
                                recommendedPeriod = recommendedPeriod.replace("'","").replace("\"","")
                                
                                data = self.fetchStockData(stockCode=ticker,period=period,duration=duration,printCounter=printCounter, start=start,end=end,proxyServer=proxyServer,)
                                return data
                            elif "YFRateLimitError" in err:
                                if attempt <= 2:
                                    default_logger().debug(f"YFRateLimitError Hit! Going for attempt : {attempt+1}")
                                    
                    else:
                        multiIndex = data.keys()
                        if isinstance(multiIndex, pd.MultiIndex):
                            listStockCodes = multiIndex.get_level_values(0)
                            data = data.get(listStockCodes[0])
                                    
            except (KeyError,YFPricesMissingError) as e: # pragma: no cover
                default_logger().debug(e,exc_info=True)
                pass
            except YFRateLimitError as e:
                default_logger().debug(f"YFRateLimitError Hit! \n{e}")
                
                pass
            except (YFInvalidPeriodError,Exception) as e: # pragma: no cover
                default_logger().debug(e,exc_info=True)                    
        if printCounter and type(screenCounter) != int:
            sys.stdout.write("\r\033[K")
            try:
                OutputControls().printOutput(
                    colorText.GREEN
                    + (
                        "[%d%%] Screened %d, Found %d. Fetching data & Analyzing %s..."
                        % (
                            int((screenCounter.value / totalSymbols) * 100),
                            screenCounter.value,
                            screenResultsCounter.value,
                            stockCode,
                        )
                    )
                    + colorText.END,
                    end="",
                )
            except ZeroDivisionError as e: # pragma: no cover
                default_logger().debug(e, exc_info=True)
                pass
            except KeyboardInterrupt: # pragma: no cover
                raise KeyboardInterrupt
            except Exception as e:  # pragma: no cover
                default_logger().debug(e, exc_info=True)
                pass
        if (data is None or len(data) == 0) and printCounter:
            OutputControls().printOutput(
                colorText.FAIL
                + "=> Failed to fetch!"
                + colorText.END,
                end="\r",
                flush=True,
            )
            raise StockDataEmptyException
        if printCounter:
            OutputControls().printOutput(
                colorText.GREEN + "=> Done!" + colorText.END,
                end="\r",
                flush=True,
            )
        return data
     # Get Daily Nifty 50 Index:
    def fetchLatestNiftyDaily(self, proxyServer=None):
        data = yf.download(
            tickers="^NSEI",
            period="5d",
            interval="1d",
            proxy=proxyServer,
            progress=False,
            timeout=self.configManager.longTimeout,
        )
        return data

    # Get Data for Five EMA strategy
    def fetchFiveEmaData(self, proxyServer=None):
        nifty_sell = yf.download(
            tickers="^NSEI",
            period="5d",
            interval="5m",
            proxy=proxyServer,
            progress=False,
            timeout=self.configManager.longTimeout,
        )
        banknifty_sell = yf.download(
            tickers="^NSEBANK",
            period="5d",
            interval="5m",
            proxy=proxyServer,
            progress=False,
            timeout=self.configManager.longTimeout,
        )
        nifty_buy = yf.download(
            tickers="^NSEI",
            period="5d",
            interval="15m",
            proxy=proxyServer,
            progress=False,
            timeout=self.configManager.longTimeout,
        )
        banknifty_buy = yf.download(
            tickers="^NSEBANK",
            period="5d",
            interval="15m",
            proxy=proxyServer,
            progress=False,
            timeout=self.configManager.longTimeout,
        )
        return nifty_buy, banknifty_buy, nifty_sell, banknifty_sell

    # Load stockCodes from the watchlist.xlsx
    def fetchWatchlist(self):
        createTemplate = False
        data = pd.DataFrame()
        try:
            data = pd.read_excel("watchlist.xlsx")
        except FileNotFoundError as e:  # pragma: no cover
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput(
                colorText.FAIL
                + f"  [+] watchlist.xlsx not found in {os.getcwd()}"
                + colorText.END
            )
            createTemplate = True
        try:
            if not createTemplate:
                data = data["Stock Code"].values.tolist()
        except KeyError as e: # pragma: no cover
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput(
                colorText.FAIL
                + '  [+] Bad Watchlist Format: First Column (A1) should have Header named "Stock Code"'
                + colorText.END
            )
            createTemplate = True
        if createTemplate:
            sample = {"Stock Code": ["SBIN", "INFY", "TATAMOTORS", "ITC"]}
            sample_data = pd.DataFrame(sample, columns=["Stock Code"])
            sample_data.to_excel("watchlist_template.xlsx", index=False, header=True)
            OutputControls().printOutput(
                colorText.BLUE
                + f"  [+] watchlist_template.xlsx created in {os.getcwd()} as a referance template."
                + colorText.END
            )
            return None
        return data
