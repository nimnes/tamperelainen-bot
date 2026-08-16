from bs4 import BeautifulSoup

from scraper import find_original_image_url


def test_prefers_diks_figure_image_over_cropped_og_image():
    html = """
    <meta property="og:image" content="https://cdn.example.com/photo-crop.jpg">
    <figure class="diks-figure__image">
      <img
        src="https://cdn.example.com/photo-800.jpg"
        srcset="
          https://cdn.example.com/photo-800.jpg 800w,
          https://cdn.example.com/photo-2400.jpg 2400w,
          https://cdn.example.com/photo-1200.jpg 1200w">
    </figure>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert find_original_image_url(soup, "https://example.com/article") == (
        "https://cdn.example.com/photo-2400.jpg"
    )


def test_diks_figure_image_can_be_a_wrapper():
    html = """
    <figure class="diks-figure__image">
      <picture>
        <source srcset="
          https://cdn.example.com/photo-600.jpg 600w,
          https://cdn.example.com/photo-2000.jpg 2000w">
        <img src="https://cdn.example.com/photo-400.jpg">
      </picture>
    </figure>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert find_original_image_url(soup, "https://example.com/article") == (
        "https://cdn.example.com/photo-2000.jpg"
    )


def test_diks_figure_data_original_is_used():
    html = """
    <figure class="diks-figure__image">
      <img
        src="https://cdn.example.com/photo-crop.jpg"
        data-original="https://cdn.example.com/photo-original.jpg">
    </figure>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert find_original_image_url(soup, "https://example.com/article") == (
        "https://cdn.example.com/photo-original.jpg"
    )


def test_falls_back_to_og_image_when_diks_figure_is_missing():
    html = """
    <meta property="og:image" content="/images/photo.jpg">
    """
    soup = BeautifulSoup(html, "html.parser")
    assert find_original_image_url(soup, "https://example.com/article") == (
        "https://example.com/images/photo.jpg"
    )
