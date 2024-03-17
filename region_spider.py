import argparse
import asyncio
import csv
import time

import httpx
from bs4 import BeautifulSoup

region_levels = [
    'province',
    'city',
    'county',
    'town',
    'village'
]


async def main():
    parser = argparse.ArgumentParser(description='Export region data to CSV file')
    parser.add_argument('--csv_file', type=str, default='', help='File to export CSV data to')
    parser.add_argument('--level', type=int, choices=range(1, 6), default=3,
                        help='Number of region levels to crawl (default: 3)')
    args = parser.parse_args()

    region_data = []
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        response = await client.get('https://www.stats.gov.cn/sj/tjbz/qhdm/')
        soup = BeautifulSoup(response.text, 'html.parser')
        latest_standard = soup.css.select_one('.list-content > ul > li')
        if not latest_standard:
            return
        latest_standard_url = latest_standard.css.select_one('a')['href']
        latest_standard_url = latest_standard_url.replace("http://", "https://")
        latest_standard_time = latest_standard.css.select_one('span').get_text(strip=True)
        await parse_region(region_data, client, latest_standard_url, 0, args.level)
        end_time = time.time()
        print(f"Total time: {end_time - start_time} seconds")
    if not args.csv_file:
        args.csv_file = f"region_data_{latest_standard_time}.csv"
    export_to_csv(region_data, args.csv_file, latest_standard_time)
    print(f"Exported region data to {args.csv_file}")


def export_to_csv(region_data, csv_file, latest_standard_time):
    fieldnames = ['id', 'code', 'name', 'type', 'parent_code', 'create_time', 'update_time', 'is_deleted']

    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for idx, region in enumerate(region_data, start=1):
            region['id'] = idx
            region['create_time'] = latest_standard_time + ' 00:00:00'
            region['update_time'] = latest_standard_time + ' 00:00:00'
            region['is_deleted'] = 0
            writer.writerow(region)


async def parse_region(region_data, client, url, region_level_index=0, max_levels=5, parent_code=None):
    if region_level_index >= max_levels:
        return

    region_type = region_levels[region_level_index]
    response = await client.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    selector = f".{region_type}table .{region_type}tr td a"
    regions = soup.select(selector)
    for region in regions:
        name = region.get_text(strip=True)
        if name.isdigit():
            continue
        href = None
        # 目前只有雄安新区
        if 'href' not in region.attrs:
            print(region.name)
            code = 133100
        else:
            href = region['href']
            code = href.split('/')[-1].split('.')[0]
        item = {
            'code': code,
            'name': name,
            'type': region_type.upper(),
            'parent_code': parent_code if parent_code else None
        }
        print(item)
        region_data.append(item)
        if href is not None:
            next_level_url = f"{url.rsplit('/', 1)[0]}/{href}"
            await parse_region(region_data, client, next_level_url, region_level_index + 1, max_levels, code)


if __name__ == "__main__":
    asyncio.run(main())
