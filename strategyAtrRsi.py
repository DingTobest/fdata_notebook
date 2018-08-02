# encoding: UTF-8

"""
一个ATR-RSI指标结合的交易策略，适合用在股指的1分钟和5分钟线上。

注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
2. 将IF0000_1min.csv用ctaHistoryData.py导入MongoDB后，直接运行本文件即可回测策略

"""

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate, 
                                                     BarGenerator, 
                                                     ArrayManager)

# 增加jqdata的输入
import jqdatasdk
from datetime import datetime, timedelta


########################################################################
class AtrRsiStrategy(CtaTemplate):
    """结合ATR和RSI指标的一个分钟线交易策略"""
    className = 'AtrRsiStrategy'
    author = u'Dingzh.Tobest'

    # 策略参数
    atrLength = 22          # 计算ATR指标的窗口数   
    atrMaLength = 10        # 计算ATR均线的窗口数
    rsiLength = 5           # 计算RSI的窗口数
    rsiEntry = 16           # RSI的开仓信号
    trailingPercent = 0.8   # 百分比移动止损
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量

    # 策略变量
    atrValue = 0                        # 最新的ATR指标数值
    atrMa = 0                           # ATR移动平均的数值
    rsiValue = 0                        # RSI指标的数值
    rsiBuy = 0                          # RSI买开阈值
    rsiSell = 0                         # RSI卖开阈值
    intraTradeHigh = 0                  # 移动止损用的持仓期内最高价
    intraTradeLow = 0                   # 移动止损用的持仓期内最低价

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'atrLength',
                 'atrMaLength',
                 'rsiLength',
                 'rsiEntry',
                 'trailingPercent']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'atrValue',
               'atrMa',
               'rsiValue',
               'rsiBuy',
               'rsiSell']  
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'intraTradeHigh',
                'intraTradeLow']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(AtrRsiStrategy, self).__init__(ctaEngine, setting)
        
        # 创建K线合成器对象
        self.bg = BarGenerator(self.onBar)
        self.am = ArrayManager()
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
        self.writeCtaLog(u'测试')

        # 获取当前日期
        self.today = str(self.ctaEngine.today)[0:10]
        print(self.today)

        # 初始化RSI入场阈值
        self.rsiBuy = 50 + self.rsiEntry
        self.rsiSell = 50 - self.rsiEntry

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        # initData = self.loadBar(self.initDays)

        # jqdata登陆
        jqdatasdk.auth(u'XXXXXXXX', u'XXXXXXX')

        initData = []
        trade_days_list = jqdatasdk.get_trade_days(end_date=self.today, count=self.initDays)

        # 获取前多日如数，按倒叙排序
        minute_df = jqdatasdk.get_price('IC1808.CCFX', start_date=trade_days_list[0], end_date=self.today, frequency='minute')  # Fix

        # 将数据转换为loadCsv中处理的数据类型，方便处理
        del minute_df['money']
        minute_df = minute_df.reset_index()
        minute_df.rename(columns={'index': 'trade_date', 'open': 'Open', 'close': 'Close', 'high': 'High', 'low': 'Low','volume': 'TotalVolume'}, inplace=True)
        minute_df["Date"] = minute_df["trade_date"].map(lambda x: str(x)[0:10])
        minute_df["Time"] = minute_df["trade_date"].map(lambda x: str(x)[11:])
        del minute_df['trade_date']

        # 将数据传入到数据队列当中
        for index, row in minute_df.iterrows():
            bar = VtBarData()
            bar.vtSymbol = "IC1808" # Fix
            bar.symbol = "IC1808"   # Fix
            bar.open = float(row['Open'])
            bar.high = float(row['High'])
            bar.low = float(row['Low'])
            bar.close = float(row['Close'])
            bar.date = datetime.strptime(row['Date'], '%Y-%m-%d').strftime('%Y%m%d')
            bar.time = row['Time']
            bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
            bar.volume = row['TotalVolume']

            initData.append(bar)
            print bar.date, bar.time

        for bar in initData:
            self.onBar(bar)

        self.putEvent()
        self.writeCtaLog(u'策略初始化成功')

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bg.updateTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.cancelAll()

        # 保存K线数据
        am = self.am
        am.updateBar(bar)
        if not am.inited:
            return

        # 计算指标数值
        atrArray = am.atr(self.atrLength, array=True)
        self.atrValue = atrArray[-1]
        self.atrMa = atrArray[-self.atrMaLength:].mean()
        
        self.rsiValue = am.rsi(self.rsiLength)

        # 判断是否要进行交易
        
        # 当前无仓位
        if self.pos == 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low

            # ATR数值上穿其移动平均线，说明行情短期内波动加大
            # 即处于趋势的概率较大，适合CTA开仓
            if self.atrValue > self.atrMa:
                # 使用RSI指标的趋势行情时，会在超买超卖区钝化特征，作为开仓信号
                if self.rsiValue > self.rsiBuy:
                    # 这里为了保证成交，选择超价5个整指数点下单
                    self.buy(bar.close+5, self.fixedSize)

                elif self.rsiValue < self.rsiSell:
                    self.short(bar.close-5, self.fixedSize)

        # 持有多头仓位
        elif self.pos > 0:
            # 计算多头持有期内的最高价，以及重置最低价
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = bar.low
            
            # 计算多头移动止损
            longStop = self.intraTradeHigh * (1-self.trailingPercent/100)

            # 发出本地止损委托
            self.sell(longStop, abs(self.pos), stop=True)
            
        # 持有空头仓位
        elif self.pos < 0:
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            self.intraTradeHigh = bar.high

            shortStop = self.intraTradeLow * (1+self.trailingPercent/100)
            self.cover(shortStop, abs(self.pos), stop=True)

        # 同步数据到数据库
        self.saveSyncData()

        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
