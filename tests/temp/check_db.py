"""检查数据库中的数据"""
from src.deepnovel.persistence import get_persistence_manager

pm = get_persistence_manager()

print('=== MongoDB ===')
if pm.mongodb_client:
    chars = list(pm.mongodb_client.get_collection('character_profiles').find({}).sort('created_at', -1).limit(3))
    print('Characters:', len(chars))
    for c in chars:
        print('  -', c.get('name'))

    locs = list(pm.mongodb_client.get_collection('world_locations').find({}).sort('created_at', -1).limit(3))
    print('Locations:', len(locs))

    chapters = list(pm.mongodb_client.get_collection('chapters').find({}).sort('created_at', -1).limit(3))
    print('Chapters:', len(chapters))
    for chap in chapters:
        content = chap.get('content', '')
        print('  - Chapter', chap.get('chapter_num'), ':', len(content.split()), 'words')
        print('    Preview:', content[:100], '...')

print()
print('=== Neo4j ===')
if pm.neo4j_client:
    result = pm.neo4j_client.execute_cypher('MATCH (n) RETURN labels(n)[0] as label, count(*) as count')
    print('Nodes:')
    for record in result:
        print(' ', record.get('label'), ':', record.get('count'))

print()
print('=== ChromaDB ===')
if pm.chromadb_client:
    print('Chunks:', pm.chromadb_client._collection.count())
