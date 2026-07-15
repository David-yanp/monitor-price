import unittest

from app.prices.google import parse_google_usd_cny_rate


class GoogleRateParseTests(unittest.TestCase):
    def test_parse_current_currency_summary_shape(self) -> None:
        html = (
            "<script>"
            "AF_initDataCallback({key: 'ds:4', data:[[["
            '"/g/11bvvzq4m1",null,null,null,null,null,null,null,6.77075,'
            'null,null,null,null,null,null,null,null,null,null,null,null,null,'
            'null,null,null,0,0,0,1,null,null,null,null,null,null,null,null,'
            'null,null,null,null,null,null,null,["USD","United States Dollar"]'
            "]]], sideChannel: {}});"
            "</script>"
        )

        self.assertEqual(parse_google_usd_cny_rate(html), 6.77075)

    def test_parse_current_af_init_data_shape(self) -> None:
        html = (
            '<script class="ds:13">'
            "AF_initDataCallback({key: 'ds:13', data:[[[["
            '"/g/11bvvzq4m1",null,"USD / CNY",3,null,'
            "[6.79415214,2.14E-6,3.15E-5,4,7,6],null,6.794149999999999,"
            'null,null,null,[1783496280],null,0,"/g/11bvvzq4m1",'
            '["USD","CNY","United States Dollar","Chinese Yuan"],null,'
            '[1783496220],null,null,null,"USD-CNY",null,null,2'
            "]]]], sideChannel: {}});</script>"
        )

        self.assertEqual(parse_google_usd_cny_rate(html), 6.79415214)

    def test_parse_dom_price_shape(self) -> None:
        html = '<div class="YMlKec fxKbKc">6.8123</div>'

        self.assertEqual(parse_google_usd_cny_rate(html), 6.8123)


if __name__ == "__main__":
    unittest.main()
