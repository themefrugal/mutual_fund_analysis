{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE DeriveGeneric #-}

-- Rolling SIP XIRR engine.
--
-- Reads a JSON payload from stdin describing a daily NAV series plus SIP
-- parameters, simulates a monthly SIP over every possible rolling window of
-- `windowYears` length, and emits the XIRR of each window as JSON to stdout.
--
-- Input:
--   { "navs": [{"date": "YYYY-MM-DD", "nav": 123.45}, ...]   -- daily, sorted or not
--   , "windowYears": 7
--   , "monthlyAmount": 1000.0
--   , "stepUpPct": 5.0
--   }
--
-- Output:
--   [ { "startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD", "xirr": 14.32 }, ... ]
--   `xirr` is null when the Newton-Raphson solve fails to converge.

module Main (main) where

import Data.Aeson
import qualified Data.ByteString.Lazy as BSL
import Data.List (foldl', sortOn)
import qualified Data.Map.Strict as Map
import Data.Map.Strict (Map)
import Data.Time.Calendar
  ( Day
  , diffDays
  , toGregorian
  , fromGregorian
  , gregorianMonthLength
  )
import GHC.Generics (Generic)
import System.IO (hSetEncoding, stdin, stdout, utf8)

data NavPoint = NavPoint
  { npDate :: Day
  , npNav  :: Double
  } deriving (Show, Generic)

instance FromJSON NavPoint where
  parseJSON = withObject "NavPoint" $ \o ->
    NavPoint <$> o .: "date" <*> o .: "nav"

data Input = Input
  { inNavs          :: [NavPoint]
  , inWindowYears   :: Int
  , inMonthlyAmount :: Double
  , inStepUpPct     :: Double
  } deriving (Show, Generic)

instance FromJSON Input where
  parseJSON = withObject "Input" $ \o ->
    Input
      <$> o .: "navs"
      <*> o .: "windowYears"
      <*> o .: "monthlyAmount"
      <*> o .:? "stepUpPct" .!= 0.0

data WindowResult = WindowResult
  { wrStartDate :: Day
  , wrEndDate   :: Day
  , wrXirr      :: Maybe Double
  }

instance ToJSON WindowResult where
  toJSON wr =
    object
      [ "startDate" .= wrStartDate wr
      , "endDate"   .= wrEndDate wr
      , "xirr"      .= wrXirr wr
      ]

-- | Last calendar day of every month spanned by [lo, hi].
monthEndDates :: Day -> Day -> [Day]
monthEndDates lo hi = go y0 m0
  where
    (y0, m0, _) = toGregorian lo
    go y m
      | end > hi  = []
      | end < lo  = next
      | otherwise = end : next
      where
        end  = fromGregorian y m (gregorianMonthLength y m)
        next
          | m == 12   = go (y + 1) 1
          | otherwise = go y (m + 1)

-- | Step-up multiplier applied every 12 installments (0-indexed).
stepUpMultiplier :: Double -> Int -> Double
stepUpMultiplier stepUpPct monthIndex =
  (1.0 + stepUpPct / 100.0) ^^ (monthIndex `div` 12)

-- | Net present value of a cashflow list at rate r, anchored at t0.
npv :: Day -> Double -> [(Day, Double)] -> Double
npv t0 r = foldl' (\acc (d, amt) -> acc + amt / (1 + r) ** years d) 0
  where
    years d = fromIntegral (diffDays d t0) / 365.0

-- | Derivative of npv with respect to r.
npv' :: Day -> Double -> [(Day, Double)] -> Double
npv' t0 r = foldl' (\acc (d, amt) -> acc + acc' d amt) 0
  where
    acc' d amt =
      let t = years d
       in if t == 0 then 0 else -amt * t / (1 + r) ** (t + 1)
    years d = fromIntegral (diffDays d t0) / 365.0

-- | Newton-Raphson solve for XIRR. Returns Nothing on non-convergence.
solveXirr :: [(Day, Double)] -> Maybe Double
solveXirr cfs
  | length cfs < 2 = Nothing
  | otherwise = go 0.1 (0 :: Int)
  where
    t0 = fst (head (sortOn fst cfs))
    go r iters
      | iters > 100 = Nothing
      | isNaN r || isInfinite r = Nothing
      | r <= (-0.999999) = Nothing
      | abs fr < 1.0e-7 = Just r
      | otherwise =
          let dr = fr / fr'
           in if isNaN dr || isInfinite dr || fr' == 0
                then Nothing
                else go (r - dr) (iters + 1)
      where
        fr  = npv t0 r cfs
        fr' = npv' t0 r cfs

-- | Simulate one rolling SIP window and compute its XIRR.
simulateWindow :: Map Day Double -> Double -> Double -> [Day] -> Maybe WindowResult
simulateWindow navMap monthlyAmount stepUpPct windowDates = do
  navs <- mapM (`Map.lookup` navMap) windowDates
  let monthIdxs    = [0 ..]
      amounts      = zipWith (\i _ -> monthlyAmount * stepUpMultiplier stepUpPct i) monthIdxs windowDates
      outflows     = zip windowDates (map negate amounts)
      units        = zipWith (/) amounts navs
      totalUnits   = sum units
      finalNav     = last navs
      finalValue   = totalUnits * finalNav
      lastDate     = last windowDates
      inflow       = (lastDate, finalValue)
      cashflows    = outflows ++ [inflow]
      result       = solveXirr cashflows
  pure WindowResult
    { wrStartDate = head windowDates
    , wrEndDate   = lastDate
    , wrXirr      = fmap (* 100) result
    }

rollingWindows :: Int -> [Day] -> [[Day]]
rollingWindows numMonths dates
  | length dates < numMonths = []
  | otherwise = windows
  where
    n        = length dates
    starts   = [0 .. n - numMonths]
    windows  = [take numMonths (drop i dates) | i <- starts]

run :: Input -> [WindowResult]
run input = concatMap (maybe [] (: [])) results
  where
    navMap        = Map.fromList [(npDate p, npNav p) | p <- inNavs input]
    dates         = Map.keys navMap
    lo            = minimum dates
    hi            = maximum dates
    monthlyDates  = monthEndDates lo hi
    numMonths     = inWindowYears input * 12
    windows       = rollingWindows numMonths monthlyDates
    results       = [ simulateWindow navMap (inMonthlyAmount input) (inStepUpPct input) w
                     | w <- windows
                     ]

main :: IO ()
main = do
  hSetEncoding stdin utf8
  hSetEncoding stdout utf8
  raw <- BSL.getContents
  case eitherDecode raw of
    Left err -> error ("Invalid input JSON: " ++ err)
    Right input -> BSL.putStr (encode (run input))
