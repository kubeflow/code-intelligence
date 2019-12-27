def assert_dict_equal(expected, actual):
  message = []
  equal = True
  for k, v in expected.items():
    if actual[k] != v:
      message.append(f"For key {k} want {v}, got {actual[k]}")
      equal = False

  for k, v in actual.items():
    if not k in expected:
      message.append(f"Got extra key {k} with value {v}")
      equal = False

  assert equal, "\n".join(message)
