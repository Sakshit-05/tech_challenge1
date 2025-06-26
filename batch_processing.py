import os
import pandas as pd
import requests
import time
from datetime import datetime
from collections import Counter
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

def get_url_status(url):
    start_time = time.time()
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        elapsed_time = round(time.time() - start_time, 3)
        code = response.status_code

        if code == 200:
            message = '✅ Site is Live'
            category = 'active'
        elif code == 404:
            message = '❌ 404 Not Found'
            category = 'inactive'
        elif code == 500:
            message = '⚠️ Server Error'
            category = 'error'
        else:
            message = f'⚠️ Status: {code}'
            category = 'error'

        return {
            'url': url,
            'status_code': code,
            'message': message,
            'response_time_sec': elapsed_time,
            'category': category
        }
    except Exception as e:
        elapsed_time = round(time.time() - start_time, 3)
        return {
            'url': url,
            'status_code': 'N/A',
            'message': f'Error: {str(e)}',
            'response_time_sec': elapsed_time,
            'category': 'error'
        }

@app.route('/file_upload', methods=['POST'])
def upload_file():
    url_list = []

    manual_url = request.form.get('url')
    if manual_url:
        url_list.append(manual_url.strip())

    file = request.files.get('file')
    if file and file.filename:
        if not file.filename.endswith(('.csv', '.xlsx')):
            return jsonify({'error': 'Only CSV and Excel files are allowed'}), 400

        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            urls = df.values.flatten()
            file_urls = [str(url).strip() for url in urls if pd.notna(url)]
            url_list.extend(file_urls)
        except Exception as e:
            return jsonify({'error': f'Failed to read file: {str(e)}'}), 500

    if not url_list:
        return jsonify({'error': 'No URL or file provided.'}), 400

    with ThreadPoolExecutor(max_workers=70) as executor:
        results = list(executor.map(get_url_status, url_list))

    summary = {}
    category_count = Counter()
    for result in results:
        code = str(result['status_code'])
        cat = result['category']
        category_count[cat] += 1

        if code not in summary:
            summary[code] = {
                'count': 0,
                'message': result['message'],
                'Urls': []
            }
        summary[code]['count'] += 1
        summary[code]['Urls'].append(result['url'])

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'message': 'URLs processed successfully',
        'processed_at': timestamp,
        'results': results,
        'summary': summary,
        'category_counts': dict(category_count)
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
