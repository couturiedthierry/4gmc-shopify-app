from pathlib import Path


source = (Path(__file__).resolve().parents[1] / 'static' / 'app.js').read_text(encoding='utf-8')

assert "if(!form.id||form.id==='login-form')return" not in source
assert "!form.classList.contains('store-connection-form')" in source
assert "typeof message==='string'?message:'Saved successfully'" in source
assert "messageText(result.detail)" in source
assert "return 'Store details saved.'" in source
assert "return 'Shopify address saved. Authorize or reconnect to publish.'" in source


assert "const launchError=launchParams.get('shopify_error')" in source
assert "catch(error){showToast(error?.message||error);}" in source
assert "refresh().catch(error=>showToast(error?.message||error))" in source
assert "else showToast(error.message)" not in source

print('Frontend form submission and notification regression checks passed')
