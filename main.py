import logging
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from string import Template
from typing import Callable

from jinja2 import Environment, FileSystemLoader

from process_csv import BASE_DIR, read_data

PORT = 8000

env = Environment(
    loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")), autoescape=True
)


def _init_logger() -> logging.Logger:
    """
    初始化日志记录器
    1. 设置日志级别为 INFO
    2. 设置日志格式为 [时间] [日志级别] 日志消息
    3. 设置时间格式为 年-月-日 时:分:秒
    4. 返回一个日志记录器实例
    5. 日志记录器可以用于记录应用程序的运行状态、调试信息和错误信息等
    6. 日志记录器可以帮助开发者更好地理解应用程序的行为和性能，并在出现问题时提供有用调试信息
    :return:
    """
    logging.basicConfig(
        level=logging.INFO,  # ✅ 设置日志级别
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


class WebServer(BaseHTTPRequestHandler):
    """
    WebServer 类继承自 http.server.BaseHTTPRequestHandler，用于处理 HTTP 请求。
    1. _serve_static 方法用于处理静态资源请求，根据文件扩展名设置正确的 MIME 类型，并将文件内容写入响应。
    2. _render_template 方法用于渲染 Jinja2 模板，读取 CSV 数据并将其传递给模板，生成 HTML 响应。
    3. do_GET 方法用于处理 GET 请求，根据请求路径匹配路由，调用相应的处理方法，或者返回 404 错误。
    4. 支持静态资源拦截，静态资源路径以 /static/ 开头，直接返回文件内容，不再继续处理其他路由。
    5. 支持路由模式匹配，使用 match-case 语法，根据请求路径调用不同的模板渲染方法。
    """

    def _serve_static(self, file_path):
        """
        处理静态资源请求，根据文件扩展名设置正确的 MIME 类型，并将文件内容写入响应。
        1. 获取文件扩展名
        2. 根据扩展名查找对应的 MIME 类型，如果未找到则使用默认的 application/octet-stream
        3. 发送 HTTP 响应头，设置状态码为 200，设置 Content-Type 为对应的 MIME 类型
        4. 打开文件并读取内容，将其写入响应体
        5. 如果文件不存在或无法读取，将返回 404 错误
        6. 支持的静态资源类型包括 CSS、PNG、JPG、SVG 和 JSON
        7. 可以根据需要扩展支持的静态资源类型
        :param file_path:
        :return:
        """
        ext = Path(file_path).suffix
        mime = {
            ".css": "text/css",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".map": "application/json",
        }.get(ext, "application/octet-stream")

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())

    def do_GET(self):
        """
        处理 GET 请求，根据请求路径匹配路由，调用相应的处理方法，或者返回 404 错误。
        1. 解析请求路径，获取 URL 的路径部分
        2. 如果路径以 /static/ 开头，调用 _serve_static 方法处理静态资源请求，并返回原始请求
        3. 如果路径匹配 /api/v1/x，调用 _render_template 方法渲染 x.jinja2 模板
        4. 如果路径匹配 /api/v1/y，调用 _render_template 方法渲染 y.jinja2 模板
        5. 如果路径不匹配任何已定义的路由，返回 404 错误
        :return:
        """
        url_path = urllib.parse.urlparse(self.path).path

        # 静态资源拦截
        if url_path.startswith("/static/"):
            file_path = (
                    Path(BASE_DIR) / "static" / url_path.removeprefix("/static/")
            ).resolve()
            if file_path.is_relative_to(Path(BASE_DIR).resolve()):
                self._serve_static(file_path)
                # 拦截静态资源后，返回原始请求，不再继续处理
                return

        # 路由模式匹配
        csv_path: str = Path(BASE_DIR) / "data/csv"
        match url_path:
            case "/":
                html = env.get_template("index.jinja2").render()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode())

            case "/industry":
                self._render_template(
                    func_csv=read_data,
                    csv_name=Path(csv_path) / "industry_chart_data.csv",
                    template_name="industry.jinja2",
                )

            case "/review":
                self._render_template(
                    func_csv=read_data,
                    csv_name=Path(csv_path) / "review_chart_data.csv",
                    template_name="review.jinja2",
                )

            case _:
                self.send_error(404)

    def _render_template(
            self,
            func_csv: Callable[[str], list[dict]],
            csv_name: str,
            template_name: Template,
    ):
        """
        渲染 Jinja2 模板，读取 CSV 数据并将其传递给模板，生成 HTML 响应。
        1. 调用 func_csv 函数读取 CSV 数据，返回一个列表字典
        2. 使用 Jinja2 环境加载指定的模板文件
        3. 将 CSV 数据传递给模板进行渲染，生成 HTML 内容
        4. 发送 HTTP 响应头，设置状态码为 200，设置 Content-Type 为 text/html
        5. 将渲染后的 HTML 内容写入响应体
        :param func_csv:
        :param template_name:
        :return:
        """
        data = func_csv(csv_name)
        html = env.get_template(template_name).render(data=data)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())


if __name__ == "__main__":
    logger = _init_logger()
    logger.info(f"Server running at http://localhost:{PORT}")
    HTTPServer(("", PORT), WebServer).serve_forever()
