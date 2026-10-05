# Usage: ruby check-config.rb <collections|fields> <rendered config.yml>
# Parse the rendered Decap config and abort unless it passes the named check.
require 'yaml'
require 'date'

Encoding.default_external = Encoding::UTF_8

EXPECTED = {
  'field-notes' => %w[title location body],
  'reading-list' => %w[title link published publish_date body],
}.freeze

def refs_left?(node)
  case node
  when Hash then node.key?('$ref') || node.values.any? { |v| refs_left?(v) }
  when Array then node.any? { |v| refs_left?(v) }
  else false
  end
end

mode = ARGV.fetch(0)
doc = YAML.safe_load(File.read(ARGV.fetch(1), encoding: 'utf-8'),
                     aliases: true, permitted_classes: [Date, Time, Symbol])
collections = doc.is_a?(Hash) ? doc['collections'] : nil
abort 'no collections list' unless collections.is_a?(Array) && collections.all?(Hash)
names = collections.map { |c| c['name'] }

case mode
when 'collections'
  abort "collections are #{names.inspect}, expected #{EXPECTED.keys.inspect}" unless names == EXPECTED.keys
  abort 'unexpanded $ref in the rendered config' if refs_left?(doc)
when 'fields'
  EXPECTED.each do |name, wanted|
    collection = collections.find { |c| c['name'] == name } or abort "missing collection #{name}"
    have = Array(collection['fields']).map { |f| f.is_a?(Hash) ? f['name'] : nil }
    missing = wanted - have
    abort "#{name} lost fields: #{missing.inspect}" unless missing.empty?
  end
else
  abort "unknown check #{mode.inspect}"
end
puts "rendered admin config ok (#{mode})"
